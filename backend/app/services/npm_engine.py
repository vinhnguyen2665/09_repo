import os
import json
import base64
import httpx
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse

from app.models.repository import Repository, RepoType
from app.models.artifact import Artifact
from app.services.storage import storage_service
from app.services.proxy_client import proxy_client
from app.core.config import settings

class NPMEngine:
    async def get_package_metadata(
        self,
        db: AsyncSession,
        repo: Repository,
        package_name: str,
        base_url: str
    ) -> Response:
        """
        Returns NPM package metadata JSON, handling Hosted, Proxy, and Group repos.
        """
        meta_path = f"{package_name}/package.json"

        # 1. Hosted repo
        if repo.type == RepoType.HOSTED:
            if await storage_service.file_exists(repo.name, meta_path):
                raw = await storage_service.read_bytes(repo.name, meta_path)
                data = json.loads(raw.decode("utf-8"))
                self._rewrite_tarball_urls(data, repo.name, base_url)
                return JSONResponse(content=data)
            raise HTTPException(status_code=404, detail=f"Package {package_name} not found in {repo.name}")

        # 2. Proxy repo
        if repo.type == RepoType.PROXY:
            # Check if cached metadata exists
            if await storage_service.file_exists(repo.name, meta_path):
                raw = await storage_service.read_bytes(repo.name, meta_path)
                data = json.loads(raw.decode("utf-8"))
                self._rewrite_tarball_urls(data, repo.name, base_url)
                return JSONResponse(content=data)

            # Lazy fetch from upstream
            if repo.upstream_url:
                upstream = f"{repo.upstream_url.rstrip('/')}/{package_name}"
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                        resp = await client.get(upstream)
                        if resp.status_code == 200:
                            data = resp.json()
                            # Cache metadata
                            await storage_service.save_bytes(
                                repo.name, meta_path, json.dumps(data, indent=2).encode("utf-8")
                            )
                            self._rewrite_tarball_urls(data, repo.name, base_url)
                            return JSONResponse(content=data)
                except Exception:
                    pass
            raise HTTPException(status_code=404, detail=f"Package {package_name} not found in proxy upstream")

        # 3. Group repo
        if repo.type == RepoType.GROUP:
            merged_versions = {}
            dist_tags = {}
            package_info = None

            for member_name in (repo.member_repo_names or []):
                stmt = select(Repository).where(Repository.name == member_name)
                res = await db.execute(stmt)
                member_repo = res.scalar_one_or_none()
                if not member_repo or not member_repo.is_online:
                    continue

                member_meta_path = f"{package_name}/package.json"
                data = None
                if await storage_service.file_exists(member_repo.name, member_meta_path):
                    raw = await storage_service.read_bytes(member_repo.name, member_meta_path)
                    data = json.loads(raw.decode("utf-8"))
                elif member_repo.type == RepoType.PROXY and member_repo.upstream_url:
                    upstream = f"{member_repo.upstream_url.rstrip('/')}/{package_name}"
                    try:
                        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                            resp = await client.get(upstream)
                            if resp.status_code == 200:
                                data = resp.json()
                                await storage_service.save_bytes(
                                    member_repo.name, member_meta_path, json.dumps(data, indent=2).encode("utf-8")
                                )
                    except Exception:
                        pass

                if data:
                    if not package_info:
                        package_info = {
                            "_id": data.get("_id", package_name),
                            "name": data.get("name", package_name),
                            "description": data.get("description", ""),
                            "readme": data.get("readme", "")
                        }
                    if "versions" in data:
                        merged_versions.update(data["versions"])
                    if "dist-tags" in data:
                        dist_tags.update(data["dist-tags"])

            if package_info:
                package_info["versions"] = merged_versions
                package_info["dist-tags"] = dist_tags
                self._rewrite_tarball_urls(package_info, repo.name, base_url)
                return JSONResponse(content=package_info)

            raise HTTPException(status_code=404, detail=f"Package {package_name} not found in group members")

        raise HTTPException(status_code=400, detail="Invalid repository type")

    async def get_tarball(
        self,
        db: AsyncSession,
        repo: Repository,
        package_name: str,
        tarball_filename: str,
        range_header: Optional[str] = None
    ) -> Response:
        """
        Handles downloading the .tgz package tarball.
        If missing from proxy repo, fetches and caches it lazily from upstream!
        """
        rel_path = f"{package_name}/-/{tarball_filename}"

        # 1. Hosted
        if repo.type == RepoType.HOSTED:
            if await storage_service.file_exists(repo.name, rel_path):
                await self._increment_download(db, repo.name, rel_path)
                return storage_service.create_streaming_response(repo.name, rel_path, range_header=range_header)
            raise HTTPException(status_code=404, detail="Tarball not found")

        # 2. Proxy
        if repo.type == RepoType.PROXY:
            if await storage_service.file_exists(repo.name, rel_path):
                await self._increment_download(db, repo.name, rel_path)
                return storage_service.create_streaming_response(repo.name, rel_path, range_header=range_header)

            # Lazy fetch from upstream
            if repo.upstream_url:
                upstream_tarball_path = f"{package_name}/-/{tarball_filename}"
                art = await proxy_client.fetch_and_cache(db, repo, rel_path, upstream_path=upstream_tarball_path)
                if art:
                    return storage_service.create_streaming_response(repo.name, rel_path, range_header=range_header)
            raise HTTPException(status_code=404, detail="Tarball not found in upstream")

        # 3. Group
        if repo.type == RepoType.GROUP:
            for member_name in (repo.member_repo_names or []):
                stmt = select(Repository).where(Repository.name == member_name)
                res = await db.execute(stmt)
                member_repo = res.scalar_one_or_none()
                if not member_repo or not member_repo.is_online:
                    continue

                if await storage_service.file_exists(member_repo.name, rel_path):
                    await self._increment_download(db, member_repo.name, rel_path)
                    return storage_service.create_streaming_response(member_repo.name, rel_path, range_header=range_header)

                if member_repo.type == RepoType.PROXY and member_repo.upstream_url:
                    upstream_tarball_path = f"{package_name}/-/{tarball_filename}"
                    art = await proxy_client.fetch_and_cache(db, member_repo, rel_path, upstream_path=upstream_tarball_path)
                    if art:
                        return storage_service.create_streaming_response(member_repo.name, rel_path, range_header=range_header)

            raise HTTPException(status_code=404, detail="Tarball not found in group members")

        raise HTTPException(status_code=400, detail="Invalid repository type")

    async def publish_package(
        self,
        db: AsyncSession,
        repo: Repository,
        package_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handles `npm publish` payload containing versions and attachments.
        """
        if repo.type != RepoType.HOSTED:
            raise HTTPException(status_code=400, detail="Can only publish to HOSTED repositories")

        package_name = package_data.get("name")
        if not package_name:
            raise HTTPException(status_code=400, detail="Invalid package data: name is required")

        meta_path = f"{package_name}/package.json"
        
        # Extract and save tarball attachments
        attachments = package_data.get("_attachments", {})
        for filename, attachment in attachments.items():
            tarball_data = base64.b64decode(attachment.get("data", ""))
            tarball_rel_path = f"{package_name}/-/{filename}"
            size, sha1_hex, md5_hex, sha256_hex = await storage_service.save_bytes(
                repo.name, tarball_rel_path, tarball_data
            )

            # Persist artifact
            stmt = select(Artifact).where(Artifact.repo_name == repo.name, Artifact.path == tarball_rel_path)
            res = await db.execute(stmt)
            art = res.scalar_one_or_none()
            if not art:
                art = Artifact(
                    repo_name=repo.name,
                    path=tarball_rel_path,
                    filename=filename,
                    size_bytes=size,
                    sha1=sha1_hex,
                    md5=md5_hex,
                    sha256=sha256_hex,
                    content_type="application/gzip",
                    is_cached_proxy=False,
                    downloads_count=0
                )
                db.add(art)
            else:
                art.size_bytes = size
                art.sha1 = sha1_hex
                art.md5 = md5_hex
                art.sha256 = sha256_hex

        # Read existing package metadata if any, and merge
        existing_data = {}
        if await storage_service.file_exists(repo.name, meta_path):
            try:
                raw = await storage_service.read_bytes(repo.name, meta_path)
                existing_data = json.loads(raw.decode("utf-8"))
            except Exception:
                pass

        merged_versions = existing_data.get("versions", {})
        merged_versions.update(package_data.get("versions", {}))
        
        merged_tags = existing_data.get("dist-tags", {})
        merged_tags.update(package_data.get("dist-tags", {}))

        final_meta = {
            "_id": package_name,
            "name": package_name,
            "description": package_data.get("description", existing_data.get("description", "")),
            "dist-tags": merged_tags,
            "versions": merged_versions,
            "readme": package_data.get("readme", existing_data.get("readme", ""))
        }

        # Save metadata
        meta_bytes = json.dumps(final_meta, indent=2).encode("utf-8")
        await storage_service.save_bytes(repo.name, meta_path, meta_bytes)
        
        # Save metadata artifact record
        stmt = select(Artifact).where(Artifact.repo_name == repo.name, Artifact.path == meta_path)
        res = await db.execute(stmt)
        meta_art = res.scalar_one_or_none()
        if not meta_art:
            meta_art = Artifact(
                repo_name=repo.name,
                path=meta_path,
                filename="package.json",
                size_bytes=len(meta_bytes),
                content_type="application/json",
                is_cached_proxy=False,
                downloads_count=0
            )
            db.add(meta_art)

        await db.commit()
        return {"ok": True, "success": True}

    def _rewrite_tarball_urls(self, data: Dict[str, Any], repo_name: str, base_url: str):
        """
        Rewrites dist.tarball URLs to point to this Zero9Repo instance.
        """
        versions = data.get("versions", {})
        package_name = data.get("name", "")
        for ver_str, ver_data in versions.items():
            if "dist" in ver_data and "tarball" in ver_data["dist"]:
                tarball_url = ver_data["dist"]["tarball"]
                filename = os.path.basename(tarball_url.split("?")[0])
                ver_data["dist"]["tarball"] = f"{base_url.rstrip('/')}/repository/{repo_name}/{package_name}/-/{filename}"

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

npm_engine = NPMEngine()
