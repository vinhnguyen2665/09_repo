import os
import shutil
import hashlib
import mimetypes
import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional, Tuple, List, Dict, Any
import aiofiles
import aiofiles.os
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from app.core.config import settings

class StorageService:
    def __init__(self, base_dir: Path = settings.STORAGE_DIR):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_safe_path(self, repo_name: str, relative_path: str) -> Path:
        # Sanitize path to prevent directory traversal
        clean_rel = os.path.normpath(relative_path.lstrip("/\\"))
        if clean_rel.startswith("..") or "/../" in clean_rel or "\\..\\" in clean_rel:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path")
        target_path = (self.base_dir / repo_name / clean_rel).resolve()
        # Ensure it stays inside base_dir
        if not str(target_path).startswith(str(self.base_dir)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access denied")
        return target_path

    async def file_exists(self, repo_name: str, relative_path: str) -> bool:
        path = self._get_safe_path(repo_name, relative_path)
        return await aiofiles.os.path.exists(path) and await aiofiles.os.path.isfile(path)

    async def dir_exists(self, repo_name: str, relative_path: str) -> bool:
        path = self._get_safe_path(repo_name, relative_path)
        return await aiofiles.os.path.exists(path) and await aiofiles.os.path.isdir(path)

    async def save_file_stream(
        self,
        repo_name: str,
        relative_path: str,
        stream: AsyncGenerator[bytes, None],
        expected_size: Optional[int] = None
    ) -> Tuple[int, str, str, str]:
        """
        Saves a stream directly to disk, calculating sha1, md5, sha256 hashes concurrently.
        Returns: (size_bytes, sha1_hex, md5_hex, sha256_hex)
        """
        target_path = self._get_safe_path(repo_name, relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        temp_path = target_path.with_name(f"{target_path.name}.tmp.{datetime.datetime.utcnow().timestamp()}")

        sha1 = hashlib.sha1()
        md5 = hashlib.md5()
        sha256 = hashlib.sha256()
        total_size = 0

        try:
            async with aiofiles.open(temp_path, "wb") as f:
                async for chunk in stream:
                    if chunk:
                        total_size += len(chunk)
                        sha1.update(chunk)
                        md5.update(chunk)
                        sha256.update(chunk)
                        await f.write(chunk)
            
            # Atomic move
            if await aiofiles.os.path.exists(target_path):
                await aiofiles.os.remove(target_path)
            await aiofiles.os.rename(temp_path, target_path)
        except Exception:
            if await aiofiles.os.path.exists(temp_path):
                await aiofiles.os.remove(temp_path)
            raise

        return total_size, sha1.hexdigest(), md5.hexdigest(), sha256.hexdigest()

    async def save_bytes(
        self,
        repo_name: str,
        relative_path: str,
        content: bytes
    ) -> Tuple[int, str, str, str]:
        target_path = self._get_safe_path(repo_name, relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        sha1 = hashlib.sha1(content).hexdigest()
        md5 = hashlib.md5(content).hexdigest()
        sha256 = hashlib.sha256(content).hexdigest()
        
        async with aiofiles.open(target_path, "wb") as f:
            await f.write(content)
            
        return len(content), sha1, md5, sha256

    async def read_bytes(self, repo_name: str, relative_path: str) -> bytes:
        target_path = self._get_safe_path(repo_name, relative_path)
        if not await aiofiles.os.path.exists(target_path):
            raise HTTPException(status_code=404, detail="File not found")
        async with aiofiles.open(target_path, "rb") as f:
            return await f.read()

    async def get_file_info(self, repo_name: str, relative_path: str) -> Optional[Dict[str, Any]]:
        target_path = self._get_safe_path(repo_name, relative_path)
        if not await aiofiles.os.path.exists(target_path) or not await aiofiles.os.path.isfile(target_path):
            return None
        stat = await aiofiles.os.stat(target_path)
        content_type, _ = mimetypes.guess_type(target_path.name)
        return {
            "size_bytes": stat.st_size,
            "modified_time": datetime.datetime.fromtimestamp(stat.st_mtime, datetime.timezone.utc),
            "content_type": content_type or "application/octet-stream"
        }

    def create_streaming_response(
        self,
        repo_name: str,
        relative_path: str,
        chunk_size: int = 65536, # 64KB
        range_header: Optional[str] = None
    ) -> StreamingResponse:
        target_path = self._get_safe_path(repo_name, relative_path)
        if not target_path.is_file():
            raise HTTPException(status_code=404, detail="Artifact not found")

        file_size = target_path.stat().st_size
        content_type, _ = mimetypes.guess_type(target_path.name)
        if not content_type:
            if target_path.name.endswith(".pom") or target_path.name.endswith(".xml"):
                content_type = "application/xml"
            elif target_path.name.endswith(".json"):
                content_type = "application/json"
            elif target_path.name.endswith(".sha1") or target_path.name.endswith(".md5"):
                content_type = "text/plain"
            else:
                content_type = "application/octet-stream"

        start = 0
        end = file_size - 1
        status_code = 200

        if range_header and range_header.startswith("bytes="):
            ranges = range_header[6:].split("-")
            if ranges[0]:
                start = int(ranges[0])
            if len(ranges) > 1 and ranges[1]:
                end = int(ranges[1])
            status_code = 206

        content_length = end - start + 1

        async def file_iterator():
            async with aiofiles.open(target_path, "rb") as f:
                if start > 0:
                    await f.seek(start)
                bytes_left = content_length
                while bytes_left > 0:
                    read_amount = min(chunk_size, bytes_left)
                    chunk = await f.read(read_amount)
                    if not chunk:
                        break
                    bytes_left -= len(chunk)
                    yield chunk

        headers = {
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{target_path.name}"',
            "ETag": f'"{hashlib.md5(f"{target_path.name}_{file_size}_{target_path.stat().st_mtime}".encode()).hexdigest()}"',
            "Last-Modified": datetime.datetime.fromtimestamp(target_path.stat().st_mtime, datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        if status_code == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

        return StreamingResponse(
            file_iterator(),
            status_code=status_code,
            media_type=content_type,
            headers=headers
        )

    async def delete_artifact(self, repo_name: str, relative_path: str) -> bool:
        target_path = self._get_safe_path(repo_name, relative_path)
        if not await aiofiles.os.path.exists(target_path):
            return False

        if await aiofiles.os.path.isdir(target_path):
            shutil.rmtree(target_path, ignore_errors=True)
        else:
            await aiofiles.os.remove(target_path)
            # Checksum companion files (.sha1, .md5, .sha256)
            for ext in [".sha1", ".md5", ".sha256"]:
                companion = target_path.with_name(f"{target_path.name}{ext}")
                if await aiofiles.os.path.exists(companion):
                    await aiofiles.os.remove(companion)

        # Cleanup parent empty directories
        parent = target_path.parent
        repo_dir = (self.base_dir / repo_name).resolve()
        while parent != repo_dir and str(parent).startswith(str(repo_dir)):
            try:
                if not os.listdir(parent):
                    os.rmdir(parent)
                    parent = parent.parent
                else:
                    break
            except Exception:
                break
        return True

    def build_file_tree(self, repo_name: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        repo_dir = (self.base_dir / repo_name).resolve()
        if not repo_dir.exists() or not repo_dir.is_dir():
            return []

        def _scan_dir(current_dir: Path, current_depth: int) -> List[Dict[str, Any]]:
            if current_depth > max_depth:
                return []
            
            nodes = []
            try:
                entries = sorted(os.scandir(current_dir), key=lambda e: (not e.is_dir(), e.name.lower()))
                for entry in entries:
                    rel_path = os.path.relpath(entry.path, repo_dir).replace("\\", "/")
                    if entry.is_dir():
                        children = _scan_dir(Path(entry.path), current_depth + 1)
                        nodes.append({
                            "name": entry.name,
                            "path": rel_path,
                            "is_dir": True,
                            "size_bytes": sum(c.get("size_bytes", 0) for c in children),
                            "children": children
                        })
                    else:
                        stat = entry.stat()
                        nodes.append({
                            "name": entry.name,
                            "path": rel_path,
                            "is_dir": False,
                            "size_bytes": stat.st_size,
                            "updated_at": datetime.datetime.fromtimestamp(stat.st_mtime, datetime.timezone.utc).isoformat(),
                            "children": None
                        })
            except Exception:
                pass
            return nodes

        return _scan_dir(repo_dir, 1)

storage_service = StorageService()
