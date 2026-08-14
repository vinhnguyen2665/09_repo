import os
import uuid
import json
import hashlib
from pathlib import Path
from typing import Optional, AsyncGenerator, Dict, Any, List
import aiofiles
import aiofiles.os
from fastapi import HTTPException, Response, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository, RepoType
from app.models.artifact import Artifact
from app.services.storage import storage_service
from app.core.config import settings

class DockerEngine:
    DOCKER_REPO_NAME = "docker-private"

    def _blob_path(self, digest: str) -> str:
        # digest format sha256:xxxx
        clean_digest = digest.replace(":", "/")
        return f"blobs/{clean_digest}"

    def _manifest_path(self, name: str, reference: str) -> str:
        clean_name = name.strip("/")
        return f"manifests/{clean_name}/{reference}.json"

    def _upload_temp_path(self, upload_uuid: str) -> Path:
        return settings.TEMP_DIR / f"docker_upload_{upload_uuid}.tmp"

    async def initiate_blob_upload(
        self,
        db: AsyncSession,
        name: str,
        digest: Optional[str] = None,
        stream: Optional[AsyncGenerator[bytes, None]] = None,
        public_url: str = settings.PUBLIC_URL
    ) -> Response:
        """
        Starts a blob upload (or monolithic upload if digest is provided).
        """
        upload_uuid = str(uuid.uuid4())
        
        # Monolithic upload
        if digest and stream:
            blob_rel_path = self._blob_path(digest)
            size, sha1_hex, md5_hex, sha256_hex = await storage_service.save_file_stream(
                self.DOCKER_REPO_NAME, blob_rel_path, stream
            )
            
            # Persist artifact
            stmt = select(Artifact).where(
                Artifact.repo_name == self.DOCKER_REPO_NAME,
                Artifact.path == blob_rel_path
            )
            res = await db.execute(stmt)
            art = res.scalar_one_or_none()
            if not art:
                art = Artifact(
                    repo_name=self.DOCKER_REPO_NAME,
                    path=blob_rel_path,
                    filename=os.path.basename(blob_rel_path),
                    size_bytes=size,
                    sha256=sha256_hex,
                    content_type="application/octet-stream",
                    is_cached_proxy=False,
                    downloads_count=0
                )
                db.add(art)
                await db.commit()

            return Response(
                status_code=201,
                headers={
                    "Location": f"/v2/{name}/blobs/{digest}",
                    "Docker-Content-Digest": digest,
                    "Docker-Distribution-API-Version": "registry/2.0",
                }
            )

        # Chunked / staged upload
        temp_file = self._upload_temp_path(upload_uuid)
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(temp_file, "wb") as f:
            pass

        return Response(
            status_code=202,
            headers={
                "Location": f"/v2/{name}/blobs/uploads/{upload_uuid}",
                "Range": "0-0",
                "Docker-Upload-UUID": upload_uuid,
                "Docker-Distribution-API-Version": "registry/2.0",
            }
        )

    async def patch_blob_upload(
        self,
        name: str,
        upload_uuid: str,
        stream: AsyncGenerator[bytes, None]
    ) -> Response:
        """
        Appends chunk data to blob upload.
        """
        temp_file = self._upload_temp_path(upload_uuid)
        if not await aiofiles.os.path.exists(temp_file):
            raise HTTPException(status_code=404, detail="Upload UUID not found")

        async with aiofiles.open(temp_file, "ab") as f:
            async for chunk in stream:
                if chunk:
                    await f.write(chunk)

        stat = await aiofiles.os.stat(temp_file)
        current_size = stat.st_size

        return Response(
            status_code=202,
            headers={
                "Location": f"/v2/{name}/blobs/uploads/{upload_uuid}",
                "Range": f"0-{max(0, current_size - 1)}",
                "Docker-Upload-UUID": upload_uuid,
                "Docker-Distribution-API-Version": "registry/2.0",
            }
        )

    async def complete_blob_upload(
        self,
        db: AsyncSession,
        name: str,
        upload_uuid: str,
        digest: str,
        stream: Optional[AsyncGenerator[bytes, None]] = None
    ) -> Response:
        """
        Completes blob upload by moving temporary file to permanent blob storage.
        """
        temp_file = self._upload_temp_path(upload_uuid)
        
        # If final chunk is sent in PUT
        if stream:
            async with aiofiles.open(temp_file, "ab") as f:
                async for chunk in stream:
                    if chunk:
                        await f.write(chunk)

        if not await aiofiles.os.path.exists(temp_file):
            raise HTTPException(status_code=404, detail="Upload UUID not found")

        # Verify digest
        sha256 = hashlib.sha256()
        async with aiofiles.open(temp_file, "rb") as f:
            while chunk := await f.read(65536):
                sha256.update(chunk)

        computed_digest = f"sha256:{sha256.hexdigest()}"
        if digest and computed_digest.lower() != digest.lower():
            await aiofiles.os.remove(temp_file)
            raise HTTPException(status_code=400, detail="Digest mismatch")

        final_digest = digest or computed_digest
        blob_rel_path = self._blob_path(final_digest)
        target_path = (settings.STORAGE_DIR / self.DOCKER_REPO_NAME / blob_rel_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if await aiofiles.os.path.exists(target_path):
            await aiofiles.os.remove(target_path)
        await aiofiles.os.rename(temp_file, target_path)

        file_size = (await aiofiles.os.stat(target_path)).st_size

        # Persist artifact
        stmt = select(Artifact).where(
            Artifact.repo_name == self.DOCKER_REPO_NAME,
            Artifact.path == blob_rel_path
        )
        res = await db.execute(stmt)
        art = res.scalar_one_or_none()
        if not art:
            art = Artifact(
                repo_name=self.DOCKER_REPO_NAME,
                path=blob_rel_path,
                filename=os.path.basename(blob_rel_path),
                size_bytes=file_size,
                sha256=sha256.hexdigest(),
                content_type="application/octet-stream",
                is_cached_proxy=False,
                downloads_count=0
            )
            db.add(art)
            await db.commit()

        return Response(
            status_code=201,
            headers={
                "Location": f"/v2/{name}/blobs/{final_digest}",
                "Docker-Content-Digest": final_digest,
                "Docker-Distribution-API-Version": "registry/2.0",
            }
        )

    async def get_blob(
        self,
        db: AsyncSession,
        name: str,
        digest: str,
        is_head: bool = False
    ) -> Response:
        """
        Retrieves or checks a Docker blob by digest.
        """
        blob_rel_path = self._blob_path(digest)
        if not await storage_service.file_exists(self.DOCKER_REPO_NAME, blob_rel_path):
            raise HTTPException(status_code=404, detail="Blob not found")

        if is_head:
            info = await storage_service.get_file_info(self.DOCKER_REPO_NAME, blob_rel_path)
            return Response(
                status_code=200,
                headers={
                    "Content-Length": str(info["size_bytes"]),
                    "Docker-Content-Digest": digest,
                    "Docker-Distribution-API-Version": "registry/2.0",
                    "Content-Type": "application/octet-stream",
                }
            )

        resp = storage_service.create_streaming_response(self.DOCKER_REPO_NAME, blob_rel_path)
        resp.headers["Docker-Content-Digest"] = digest
        resp.headers["Docker-Distribution-API-Version"] = "registry/2.0"
        return resp

    async def put_manifest(
        self,
        db: AsyncSession,
        name: str,
        reference: str,
        manifest_bytes: bytes,
        content_type: str
    ) -> Response:
        """
        Stores an image manifest JSON.
        """
        manifest_digest = f"sha256:{hashlib.sha256(manifest_bytes).hexdigest()}"
        
        # Save tag reference
        tag_path = self._manifest_path(name, reference)
        await storage_service.save_bytes(self.DOCKER_REPO_NAME, tag_path, manifest_bytes)

        # Save digest reference
        digest_path = self._manifest_path(name, manifest_digest)
        await storage_service.save_bytes(self.DOCKER_REPO_NAME, digest_path, manifest_bytes)

        # Persist artifact
        stmt = select(Artifact).where(
            Artifact.repo_name == self.DOCKER_REPO_NAME,
            Artifact.path == tag_path
        )
        res = await db.execute(stmt)
        art = res.scalar_one_or_none()
        if not art:
            art = Artifact(
                repo_name=self.DOCKER_REPO_NAME,
                path=tag_path,
                filename=f"{reference}.json",
                size_bytes=len(manifest_bytes),
                sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                content_type=content_type,
                is_cached_proxy=False,
                downloads_count=0
            )
            db.add(art)
            await db.commit()

        return Response(
            status_code=201,
            headers={
                "Location": f"/v2/{name}/manifests/{reference}",
                "Docker-Content-Digest": manifest_digest,
                "Docker-Distribution-API-Version": "registry/2.0",
            }
        )

    async def get_manifest(
        self,
        db: AsyncSession,
        name: str,
        reference: str,
        is_head: bool = False
    ) -> Response:
        """
        Retrieves or checks manifest for tag or digest.
        """
        manifest_path = self._manifest_path(name, reference)
        if not await storage_service.file_exists(self.DOCKER_REPO_NAME, manifest_path):
            raise HTTPException(status_code=404, detail="Manifest not found")

        content = await storage_service.read_bytes(self.DOCKER_REPO_NAME, manifest_path)
        digest = f"sha256:{hashlib.sha256(content).hexdigest()}"

        # Detect schema content-type
        content_type = "application/vnd.docker.distribution.manifest.v2+json"
        try:
            parsed = json.loads(content.decode("utf-8"))
            if "mediaType" in parsed:
                content_type = parsed["mediaType"]
        except Exception:
            pass

        if is_head:
            return Response(
                status_code=200,
                headers={
                    "Content-Length": str(len(content)),
                    "Content-Type": content_type,
                    "Docker-Content-Digest": digest,
                    "Docker-Distribution-API-Version": "registry/2.0",
                }
            )

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Docker-Content-Digest": digest,
                "Docker-Distribution-API-Version": "registry/2.0",
            }
        )

    async def list_tags(self, db: AsyncSession, name: str) -> JSONResponse:
        """
        Lists all available tags for an image repository.
        """
        manifest_dir = settings.STORAGE_DIR / self.DOCKER_REPO_NAME / "manifests" / name.strip("/")
        tags = []
        if manifest_dir.exists() and manifest_dir.is_dir():
            for f in manifest_dir.glob("*.json"):
                tag_name = f.stem
                if not tag_name.startswith("sha256:"):
                    tags.append(tag_name)

        return JSONResponse(
            content={
                "name": name,
                "tags": sorted(tags)
            },
            headers={"Docker-Distribution-API-Version": "registry/2.0"}
        )

docker_engine = DockerEngine()
