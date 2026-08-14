import os
import xml.etree.ElementTree as ET
import defusedxml.ElementTree as DefusedET
from typing import Optional, List, AsyncGenerator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse

from app.models.repository import Repository, RepoType, RepoFormat
from app.models.artifact import Artifact
from app.services.storage import storage_service
from app.services.proxy_client import proxy_client

class MavenEngine:
    async def get_artifact(
        self,
        db: AsyncSession,
        repo: Repository,
        relative_path: str,
        range_header: Optional[str] = None
    ) -> Response:
        """
        Handles GET for Maven artifacts (.jar, .pom, .sha1, .md5, maven-metadata.xml).
        Supports Hosted, Proxy, and Group repositories.
        """
        relative_path = relative_path.lstrip("/")

        # Special handling for maven-metadata.xml in Group repos
        if repo.type == RepoType.GROUP and relative_path.endswith("maven-metadata.xml"):
            merged_xml = await self.merge_group_metadata(db, repo, relative_path)
            if merged_xml:
                return Response(content=merged_xml, media_type="application/xml")
            raise HTTPException(status_code=404, detail="Metadata not found in group members")

        # 1. If it's a HOSTED repo: Check local storage
        if repo.type == RepoType.HOSTED:
            if await storage_service.file_exists(repo.name, relative_path):
                await self._increment_download(db, repo.name, relative_path)
                return storage_service.create_streaming_response(repo.name, relative_path, range_header=range_header)
            raise HTTPException(status_code=404, detail=f"Artifact {relative_path} not found in hosted repo {repo.name}")

        # 2. If it's a PROXY repo: Check local cache first; if missing, fetch & cache from upstream
        if repo.type == RepoType.PROXY:
            if await storage_service.file_exists(repo.name, relative_path):
                await self._increment_download(db, repo.name, relative_path)
                return storage_service.create_streaming_response(repo.name, relative_path, range_header=range_header)
            
            # Fetch from upstream and cache locally
            artifact = await proxy_client.fetch_and_cache(db, repo, relative_path)
            if artifact:
                return storage_service.create_streaming_response(repo.name, relative_path, range_header=range_header)
            raise HTTPException(status_code=404, detail=f"Artifact {relative_path} not found in upstream for {repo.name}")

        # 3. If it's a GROUP repo: Iterate member repos in priority order
        if repo.type == RepoType.GROUP:
            members = repo.member_repo_names or []
            for member_name in members:
                member_stmt = select(Repository).where(Repository.name == member_name)
                member_res = await db.execute(member_stmt)
                member_repo = member_res.scalar_one_or_none()
                if not member_repo or not member_repo.is_online:
                    continue

                # Check if available in member
                try:
                    if member_repo.type == RepoType.HOSTED:
                        if await storage_service.file_exists(member_repo.name, relative_path):
                            await self._increment_download(db, member_repo.name, relative_path)
                            return storage_service.create_streaming_response(member_repo.name, relative_path, range_header=range_header)
                    elif member_repo.type == RepoType.PROXY:
                        if await storage_service.file_exists(member_repo.name, relative_path):
                            await self._increment_download(db, member_repo.name, relative_path)
                            return storage_service.create_streaming_response(member_repo.name, relative_path, range_header=range_header)
                        # Fetch and cache in the proxy member repo
                        art = await proxy_client.fetch_and_cache(db, member_repo, relative_path)
                        if art:
                            return storage_service.create_streaming_response(member_repo.name, relative_path, range_header=range_header)
                except Exception:
                    continue

            raise HTTPException(status_code=404, detail=f"Artifact {relative_path} not found in group members")

        raise HTTPException(status_code=400, detail="Invalid repository type")

    async def put_artifact(
        self,
        db: AsyncSession,
        repo: Repository,
        relative_path: str,
        stream: AsyncGenerator[bytes, None]
    ) -> dict:
        """
        Handles PUT for Maven uploads (e.g. `mvn deploy` or Gradle `publish`).
        Only permitted on HOSTED repositories.
        Automatically computes SHA1, MD5, and creates companion hash files if not a checksum itself.
        """
        if repo.type != RepoType.HOSTED:
            raise HTTPException(status_code=400, detail="Cannot upload to Proxy or Group repositories")

        relative_path = relative_path.lstrip("/")
        size, sha1_hex, md5_hex, sha256_hex = await storage_service.save_file_stream(
            repo_name=repo.name,
            relative_path=relative_path,
            stream=stream
        )

        filename = os.path.basename(relative_path)
        is_checksum_file = any(relative_path.endswith(ext) for ext in [".sha1", ".md5", ".sha256", ".sha512"])

        # Create companion checksum files if it's a primary artifact/pom
        if not is_checksum_file:
            await storage_service.save_bytes(repo.name, f"{relative_path}.sha1", sha1_hex.encode("utf-8"))
            await storage_service.save_bytes(repo.name, f"{relative_path}.md5", md5_hex.encode("utf-8"))

        # Save or update in DB
        stmt = select(Artifact).where(Artifact.repo_name == repo.name, Artifact.path == relative_path)
        res = await db.execute(stmt)
        artifact = res.scalar_one_or_none()

        if artifact:
            artifact.size_bytes = size
            artifact.sha1 = sha1_hex
            artifact.md5 = md5_hex
            artifact.sha256 = sha256_hex
        else:
            artifact = Artifact(
                repo_name=repo.name,
                path=relative_path,
                filename=filename,
                size_bytes=size,
                sha1=sha1_hex,
                md5=md5_hex,
                sha256=sha256_hex,
                is_cached_proxy=False,
                downloads_count=0
            )
            db.add(artifact)

        await db.commit()
        return {
            "status": "success",
            "path": relative_path,
            "size": size,
            "sha1": sha1_hex,
            "md5": md5_hex
        }

    async def merge_group_metadata(self, db: AsyncSession, group_repo: Repository, metadata_path: str) -> Optional[bytes]:
        """
        Dynamically merges maven-metadata.xml across all members in a Group repository.
        """
        all_versions = set()
        group_id = None
        artifact_id = None
        latest_timestamp = "0"
        
        members = group_repo.member_repo_names or []
        for member_name in members:
            stmt = select(Repository).where(Repository.name == member_name)
            res = await db.execute(stmt)
            member_repo = res.scalar_one_or_none()
            if not member_repo:
                continue

            xml_bytes = None
            if await storage_service.file_exists(member_repo.name, metadata_path):
                xml_bytes = await storage_service.read_bytes(member_repo.name, metadata_path)
            elif member_repo.type == RepoType.PROXY and member_repo.upstream_url:
                # Attempt to fetch proxy metadata
                art = await proxy_client.fetch_and_cache(db, member_repo, metadata_path)
                if art:
                    xml_bytes = await storage_service.read_bytes(member_repo.name, metadata_path)

            if xml_bytes:
                try:
                    root = DefusedET.fromstring(xml_bytes)
                    gid = root.findtext("groupId")
                    aid = root.findtext("artifactId")
                    if gid: group_id = gid
                    if aid: artifact_id = aid
                    
                    versioning = root.find("versioning")
                    if versioning is not None:
                        versions_elem = versioning.find("versions")
                        if versions_elem is not None:
                            for v in versions_elem.findall("version"):
                                if v.text:
                                    all_versions.add(v.text.strip())
                        last_updated = versioning.findtext("lastUpdated")
                        if last_updated and last_updated > latest_timestamp:
                            latest_timestamp = last_updated
                except Exception:
                    continue

        if not all_versions and not group_id:
            return None

        # Build merged XML
        root = ET.Element("metadata")
        if group_id:
            ET.SubElement(root, "groupId").text = group_id
        if artifact_id:
            ET.SubElement(root, "artifactId").text = artifact_id

        versioning = ET.SubElement(root, "versioning")
        
        # Sort versions semantically / alphabetically
        sorted_versions = sorted(list(all_versions))
        latest_ver = sorted_versions[-1] if sorted_versions else ""
        
        ET.SubElement(versioning, "latest").text = latest_ver
        ET.SubElement(versioning, "release").text = latest_ver
        
        versions_elem = ET.SubElement(versioning, "versions")
        for v in sorted_versions:
            ET.SubElement(versions_elem, "version").text = v

        if latest_timestamp != "0":
            ET.SubElement(versioning, "lastUpdated").text = latest_timestamp

        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    async def _increment_download(self, db: AsyncSession, repo_name: str, path: str):
        try:
            stmt = select(Artifact).where(Artifact.repo_name == repo_name, Artifact.path == path)
            res = await db.execute(stmt)
            art = res.scalar_one_or_none()
            if art:
                art.downloads_count += 1
                await db.commit()
        except Exception:
            pass

maven_engine = MavenEngine()
