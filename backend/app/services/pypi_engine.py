import os
import re
import html
import json
import urllib.parse
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

    def _build_upstream_simple_url(self, base_url: str, pkg_name: str) -> str:
        base = base_url.rstrip("/")
        if base.endswith("/simple"):
            return f"{base}/{pkg_name}/"
        return f"{base}/simple/{pkg_name}/"

    def _extract_package_name_from_filename(self, filename: str) -> str:
        base = filename
        for ext in [".tar.gz", ".whl", ".zip", ".tar.bz2", ".tgz"]:
            if base.endswith(ext):
                base = base[:-len(ext)]
                break
        parts = re.split(r"[-_](?=\d)", base)
        return self._normalize_name(parts[0]) if parts else self._normalize_name(base)

    async def _get_or_fetch_upstream_mapping(self, repo: Repository, norm_name: str) -> Dict[str, Dict[str, str]]:
        """
        Returns a mapping of {filename: {"url": full_url, "hash": hash_suffix}}
        Caches locally in .metadata/pypi/{norm_name}.json inside storage.
        """
        meta_rel = f".metadata/pypi/{norm_name}.json"
        if await storage_service.file_exists(repo.name, meta_rel):
            try:
                raw = await storage_service.read_bytes(repo.name, meta_rel)
                data = json.loads(raw.decode("utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

        mapping: Dict[str, Dict[str, str]] = {}
        if not repo.upstream_url:
            return mapping

        upstream_url = self._build_upstream_simple_url(repo.upstream_url, norm_name)
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={"Accept": "text/html, application/vnd.pypi.simple.v1+json", "User-Agent": "pip/23.0"}
            ) as client:
                resp = await client.get(upstream_url)
                if resp.status_code == 200:
                    href_matches = re.findall(r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"[^>]*>([^<]+)</a>', resp.text)
                    for raw_href, raw_text in href_matches:
                        fn = raw_text.strip()
                        clean_href = raw_href.strip()
                        hash_match = re.search(r'#(sha256=[a-f0-9]+)', clean_href)
                        hash_suffix = f"#{hash_match.group(1)}" if hash_match else ""
                        orig_url_without_hash = clean_href.split("#")[0]
                        full_download_url = urllib.parse.urljoin(upstream_url, orig_url_without_hash)
                        mapping[fn] = {
                            "url": full_download_url,
                            "hash": hash_suffix
                        }

                    if mapping:
                        await storage_service.save_bytes(
                            repo.name, meta_rel, json.dumps(mapping, indent=2).encode("utf-8")
                        )
        except Exception:
            pass

        return mapping

    async def get_simple_index(
        self,
        db: AsyncSession,
        repo: Repository
    ) -> Response:
        """
        PEP 503 root listing of all package names.
        """
        if repo.type == RepoType.GROUP:
            member_names = repo.member_repo_names or []
            stmt = select(Artifact.filename).where(
                Artifact.repo_name.in_(member_names),
                Artifact.path.like("packages/%")
            )
        else:
            stmt = select(Artifact.filename).where(
                Artifact.repo_name == repo.name,
                Artifact.path.like("packages/%")
            )
        res = await db.execute(stmt)
        filenames = res.scalars().all()

        package_names = set()
        for fn in filenames:
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
        links: List[Dict[str, str]] = []

        async def collect_local_files(r_name: str):
            stmt = select(Artifact).where(
                Artifact.repo_name == r_name,
                Artifact.path.like("packages/%")
            )
            res = await db.execute(stmt)
            for art in res.scalars().all():
                fn_norm = self._normalize_name(art.filename.split("-")[0])
                if fn_norm == norm_name:
                    file_url = f"/repository/{repo.name}/packages/{art.filename}"
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
            mapping = await self._get_or_fetch_upstream_mapping(repo, norm_name)
            for fn, info in mapping.items():
                hash_part = info.get("hash", "")
                links.append({
                    "href": f"/repository/{repo.name}/packages/{fn}{hash_part}",
                    "text": fn
                })

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
                    mapping = await self._get_or_fetch_upstream_mapping(member_repo, norm_name)
                    for fn, info in mapping.items():
                        hash_part = info.get("hash", "")
                        links.append({
                            "href": f"/repository/{repo.name}/packages/{fn}{hash_part}",
                            "text": fn
                        })

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

            # Lazy fetch from upstream PyPI
            if repo.upstream_url:
                pkg_name = self._extract_package_name_from_filename(filename)
                mapping = await self._get_or_fetch_upstream_mapping(repo, pkg_name)
                upstream_info = mapping.get(filename)
                if upstream_info:
                    upstream_download_url = upstream_info["url"] if isinstance(upstream_info, dict) else str(upstream_info)
                    art = await proxy_client.fetch_and_cache(db, repo, rel_path, upstream_path=upstream_download_url)
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
                    pkg_name = self._extract_package_name_from_filename(filename)
                    mapping = await self._get_or_fetch_upstream_mapping(member_repo, pkg_name)
                    upstream_info = mapping.get(filename)
                    if upstream_info:
                        upstream_download_url = upstream_info["url"] if isinstance(upstream_info, dict) else str(upstream_info)
                        art = await proxy_client.fetch_and_cache(db, member_repo, rel_path, upstream_path=upstream_download_url)
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
