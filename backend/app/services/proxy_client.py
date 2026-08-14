import os
import httpx
import logging
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.storage import storage_service
from app.models.artifact import Artifact
from app.models.repository import Repository

logger = logging.getLogger("zero9repo.proxy")

class ProxyClient:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Zero9Repo-Proxy/1.0.0"}
        )

    async def close(self):
        await self.client.aclose()

    async def fetch_and_cache(
        self,
        db: AsyncSession,
        repo: Repository,
        relative_path: str,
        upstream_path: Optional[str] = None,
        custom_headers: Optional[dict] = None
    ) -> Optional[Artifact]:
        """
        Fetches an artifact from the repository's upstream URL,
        caches it locally in storage, records it in the database as a cached artifact,
        and returns the Artifact record.
        """
        if not repo.upstream_url:
            return None

        # Build full upstream URL
        base_upstream = repo.upstream_url.rstrip("/")
        rel = (upstream_path or relative_path).lstrip("/")
        full_upstream_url = f"{base_upstream}/{rel}"

        req_headers = {"User-Agent": "Zero9Repo-Proxy/1.0.0"}
        if custom_headers:
            req_headers.update(custom_headers)

        try:
            # Stream the response from upstream
            async with self.client.stream("GET", full_upstream_url, headers=req_headers) as response:
                if response.status_code != 200:
                    logger.warning(f"Upstream returned {response.status_code} for {full_upstream_url}")
                    return None

                content_type = response.headers.get("content-type", "application/octet-stream")
                
                # Stream into local storage
                async def stream_gen():
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        yield chunk

                size, sha1_hex, md5_hex, sha256_hex = await storage_service.save_file_stream(
                    repo_name=repo.name,
                    relative_path=relative_path,
                    stream=stream_gen()
                )

                # Persist or update artifact record in DB
                stmt = select(Artifact).where(
                    Artifact.repo_name == repo.name,
                    Artifact.path == relative_path
                )
                res = await db.execute(stmt)
                artifact = res.scalar_one_or_none()

                filename = os.path.basename(relative_path)

                if artifact:
                    artifact.size_bytes = size
                    artifact.sha1 = sha1_hex
                    artifact.md5 = md5_hex
                    artifact.sha256 = sha256_hex
                    artifact.content_type = content_type
                    artifact.is_cached_proxy = True
                    artifact.downloads_count += 1
                else:
                    artifact = Artifact(
                        repo_name=repo.name,
                        path=relative_path,
                        filename=filename,
                        size_bytes=size,
                        content_type=content_type,
                        sha1=sha1_hex,
                        md5=md5_hex,
                        sha256=sha256_hex,
                        is_cached_proxy=True,
                        downloads_count=1
                    )
                    db.add(artifact)

                await db.commit()
                await db.refresh(artifact)
                logger.info(f"Successfully cached {relative_path} in {repo.name} from {full_upstream_url}")
                return artifact

        except Exception as e:
            logger.error(f"Failed to fetch and cache {full_upstream_url}: {str(e)}")
            return None

proxy_client = ProxyClient()
