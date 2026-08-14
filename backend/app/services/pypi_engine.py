import os
import re
import html
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Response, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from app.models.repository import Repository, RepoType
from app.models.artifact import Artifact
from app.services.storage import storage_service
from app.services.proxy_client import proxy_client

class PyPIEngine:
    def _normalize_name(self, name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    async def get_simple_index(
        self,
        db: AsyncSession,
        repo: Repository
    ) -> Response:
        """
        PEP 503 root listing of all package names.
        """
        # Query distinct packages in this repo
        stmt = select(Artifact.filename).where(
            Artifact.repo_name == repo.name,
            Artifact.path.like("packages/%")
        )
        res = await db.execute(stmt)
        filenames = res.scalars().all()

        package_names = set()
        for fn in filenames:
            # Extract package name before version/ext
            # e.g., requests-2.31.0-py3-none-any.whl -> requests
            parts = fn.split("-")
            if parts:
                package_names.add(self._normalize_name(parts[0]))

        links_html = "".join(f'<a href="{pkg}/">{pkg}</a><br/>\n' for pkg in sorted(package_names))
        html_doc = f"""<!DOCTYPE html>
<html>
<head><title>Simple Index - {repo.name}</title></head>
<body>
<h1>Zero9Repo Simple Index: {repo.name}</h1>
{links_html}
</body>
</html>"""
        return HTMLResponse(content=html_doc)

    async def get_package_page(
        self,
        db: AsyncSession,
        repo: Repository,
        package_name: str,
        base_url: str
    ) -> Response:
        """
        PEP 503 package page listing downloadable distribution files (.whl, .tar.gz).
        Supports Hosted, Proxy (upstream fetching and caching links), and Group.
        """
        norm_name = self._normalize_name(package_name)
        links: List[Dict[str, str]] = [] # list of {"href": ..., "text": ..., "hash": ...}

        # Helper to gather local files
        async def collect_local_files(r_name: str):
            stmt = select(Artifact).where(
                Artifact.repo_name == r_name,
                Artifact.path.like("packages/%")
            )
            res = await db.execute(stmt)
            for art in res.scalars().all():
                fn_norm = self._normalize_name(art.filename.split("-")[0])
                if fn_norm == norm_name:
                    file_url = f"{base_url.rstrip('/')}/repository/{r_name}/packages/{art.filename}"
                    hash_part = f"#sha256={art.sha256}" if art.sha256 else ""
                    links.append({
                        "href": f"{file_url}{hash_part}",
                        "text": art.filename
                    })

        if repo.type == RepoType.HOSTED:
            await collect_local_files(repo.name)
            if not links:
                raise HTTPException(status_code=404, detail=f"Package {package_name} not found in {repo.name}")

        elif repo.type == RepoType.PROXY:
            await collect_local_files(repo.name)
            # Query upstream PyPI simple index
            if repo.upstream_url:
                upstream_url = f"{repo.upstream_url.rstrip('/')}/simple/{norm_name}/"
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers={"Accept": "text/html, application/vnd.pypi.simple.v1+json"}) as client:
                        resp = await client.get(upstream_url)
                        if resp.status_code == 200:
                            # Extract links from upstream HTML
                            href_matches = re.findall(r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"[^>]*>([^<]+)</a>', resp.text)
                            for raw_href, raw_text in href_matches:
                                fn = raw_text.strip()
                                # Clean link and rewrite to proxy download endpoint
                                clean_href = raw_href.strip()
                                proxy_download_url = f"{base_url.rstrip('/')}/repository/{repo.name}/packages/{fn}"
                                # Keep hash if present
                                hash_match = re.search(r'#(sha256=[a-f0-9]+)', clean_href)
                                hash_suffix = f"#{hash_match.group(1)}" if hash_match else ""
                                links.append({
                                    "href": f"{proxy_download_url}{hash_suffix}",
                                    "text": fn,
                                    "original_url": clean_href
                                })
                except Exception:
                    pass

            if not links:
                raise HTTPException(status_code=404, detail=f"Package {package_name} not found in proxy upstream")

        elif repo.type == RepoType.GROUP:
            for member_name in (repo.member_repo_names or []):
                stmt = select(Repository).where(Repository.name == member_name)
                res = await db.execute(stmt)
                member_repo = res.scalar_one_or_none()
                if not member_repo or not member_repo.is_online:
                    continue

                if member_repo.type == RepoType.HOSTED:
                    await collect_local_files(member_repo.name)
                elif member_repo.type == RepoType.PROXY and member_repo.upstream_url:
                    await collect_local_files(member_repo.name)
                    # Query proxy upstream
                    upstream_url = f"{member_repo.upstream_url.rstrip('/')}/simple/{norm_name}/"
                    try:
                        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, headers={"Accept": "text/html"}) as client:
                            resp = await client.get(upstream_url)
                            if resp.status_code == 200:
                                href_matches = re.findall(r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"[^>]*>([^<]+)</a>', resp.text)
                                for raw_href, raw_text in href_matches:
                                    fn = raw_text.strip()
                                    clean_href = raw_href.strip()
                                    proxy_download_url = f"{base_url.rstrip('/')}/repository/{member_repo.name}/packages/{fn}"
                                    hash_match = re.search(r'#(sha256=[a-f0-9]+)', clean_href)
                                    hash_suffix = f"#{hash_match.group(1)}" if hash_match else ""
                                    links.append({
                                        "href": f"{proxy_download_url}{hash_suffix}",
                                        "text": fn
                                    })
                    except Exception:
                        pass

            if not links:
                raise HTTPException(status_code=404, detail=f"Package {package_name} not found in group members")

        # Deduplicate links by text
        seen_texts = set()
        unique_links = []
        for l in links:
            if l["text"] not in seen_texts:
                seen_texts.add(l["text"])
                unique_links.append(l)

        links_html = "".join(f'<a href="{l["href"]}">{html.escape(l["text"])}</a><br/>\n' for l in unique_links)
        html_doc = f"""<!DOCTYPE html>
<html>
<head><title>Links for {package_name}</title></head>
<body>
<h1>Links for {package_name}</h1>
{links_html}
</body>
</html>"""
        return HTMLResponse(content=html_doc)

    async def get_package_file(
        self,
        db: AsyncSession,
        repo: Repository,
        filename: str,
        range_header: Optional[str] = None
    ) -> Response:
        """
        Downloads a wheel or sdist package file.
        If missing in proxy repo, fetches and caches it lazily from upstream PyPI!
        """
        rel_path = f"packages/{filename}"

        if repo.type == RepoType.HOSTED:
            if await storage_service.file_exists(repo.name, rel_path):
                await self._increment_download(db, repo.name, rel_path)
                return storage_service.create_streaming_response(repo.name, rel_path, range_header=range_header)
            raise HTTPException(status_code=404, detail="Package file not found")

        elif repo.type == RepoType.PROXY:
            if await storage_service.file_exists(repo.name, rel_path):
                await self._increment_download(db, repo.name, rel_path)
                return storage_service.create_streaming_response(repo.name, rel_path, range_header=range_header)

            # Lazy fetch from upstream PyPI packages
            if repo.upstream_url:
                upstream_file_path = f"packages/{filename}"
                art = await proxy_client.fetch_and_cache(db, repo, rel_path, upstream_path=upstream_file_path)
                if art:
                    return storage_service.create_streaming_response(repo.name, rel_path, range_header=range_header)
            raise HTTPException(status_code=404, detail="Package file not found in upstream")

        elif repo.type == RepoType.GROUP:
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
                    upstream_file_path = f"packages/{filename}"
                    art = await proxy_client.fetch_and_cache(db, member_repo, rel_path, upstream_path=upstream_file_path)
                    if art:
                        return storage_service.create_streaming_response(member_repo.name, rel_path, range_header=range_header)

            raise HTTPException(status_code=404, detail="Package file not found in group members")

        raise HTTPException(status_code=400, detail="Invalid repository type")

    async def upload_package(
        self,
        db: AsyncSession,
        repo: Repository,
        file: UploadFile,
        name: str,
        version: str
    ) -> Dict[str, Any]:
        """
        Handles `twine upload` multipart file submission.
        """
        if repo.type != RepoType.HOSTED:
            raise HTTPException(status_code=400, detail="Can only upload packages to HOSTED repositories")

        filename = file.filename or f"{name}-{version}.whl"
        rel_path = f"packages/{filename}"

        async def stream_gen():
            while chunk := await file.read(65536):
                yield chunk

        size, sha1_hex, md5_hex, sha256_hex = await storage_service.save_file_stream(
            repo.name, rel_path, stream_gen()
        )

        stmt = select(Artifact).where(Artifact.repo_name == repo.name, Artifact.path == rel_path)
        res = await db.execute(stmt)
        art = res.scalar_one_or_none()
        if not art:
            art = Artifact(
                repo_name=repo.name,
                path=rel_path,
                filename=filename,
                size_bytes=size,
                sha1=sha1_hex,
                md5=md5_hex,
                sha256=sha256_hex,
                content_type="application/octet-stream",
                is_cached_proxy=False,
                downloads_count=0
            )
            db.add(art)
        else:
            art.size_bytes = size
            art.sha1 = sha1_hex
            art.md5 = md5_hex
            art.sha256 = sha256_hex

        await db.commit()
        return {
            "status": "success",
            "filename": filename,
            "size": size,
            "sha256": sha256_hex
        }

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

pypi_engine = PyPIEngine()
