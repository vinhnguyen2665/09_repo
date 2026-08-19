import os
import mimetypes
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import require_reader, require_developer, get_current_user
from app.models.artifact import Artifact
from app.models.repository import Repository
from app.models.user import User
from app.schemas.artifact import FileTreeNode, ArtifactOut, FilePreviewResponse
from app.services.storage import storage_service

router = APIRouter(prefix="/storage", tags=["Storage Explorer"])

def merge_trees(trees: List[dict]) -> List[dict]:
    merged_nodes_by_name = {}
    for tree in trees:
        for node in tree:
            name = node["name"]
            if name not in merged_nodes_by_name:
                merged_nodes_by_name[name] = dict(node)
                if node.get("is_dir") and node.get("children"):
                    merged_nodes_by_name[name]["children"] = [dict(c) for c in node["children"]]
            else:
                existing = merged_nodes_by_name[name]
                if existing.get("is_dir") and node.get("is_dir"):
                    existing_children = existing.get("children") or []
                    node_children = node.get("children") or []
                    existing["children"] = merge_trees([existing_children, node_children])
                    existing["size_bytes"] = sum(c.get("size_bytes", 0) for c in existing["children"])
    return sorted(
        merged_nodes_by_name.values(),
        key=lambda e: (not e.get("is_dir"), e.get("name", "").lower())
    )

@router.get("/tree", response_model=List[FileTreeNode])
async def get_repository_file_tree(
    repo_name: str = Query(..., description="Repository name"),
    current_user: User = Depends(require_reader),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    
    if repo and repo.type.value == "group":
        member_names = repo.member_repo_names or []
        member_trees = [storage_service.build_file_tree(m_name) for m_name in member_names]
        tree = merge_trees(member_trees)
    else:
        tree = storage_service.build_file_tree(repo_name)
        
    return [FileTreeNode.model_validate(node) for node in tree]

@router.get("/inspect", response_model=ArtifactOut)
async def inspect_artifact(
    repo_name: str = Query(..., description="Repository name"),
    path: str = Query(..., description="Relative file path"),
    current_user: User = Depends(require_reader),
    db: AsyncSession = Depends(get_db)
):
    path = path.lstrip("/")
    
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    
    search_repos = [repo_name]
    if repo and repo.type.value == "group":
        search_repos = repo.member_repo_names or []
        
    art = None
    target_repo_name = None
    
    # 1. Search in DB first
    for r_name in search_repos:
        stmt = select(Artifact).where(Artifact.repo_name == r_name, Artifact.path == path)
        res = await db.execute(stmt)
        art = res.scalar_one_or_none()
        if art:
            target_repo_name = r_name
            break
            
    if not art:
        # 2. Check if file exists on disk
        for r_name in search_repos:
            info = await storage_service.get_file_info(r_name, path)
            if info:
                target_repo_name = r_name
                filename = os.path.basename(path)
                art = Artifact(
                    repo_name=r_name,
                    path=path,
                    filename=filename,
                    size_bytes=info["size_bytes"],
                    content_type=info["content_type"],
                    is_cached_proxy=False,
                    downloads_count=0
                )
                db.add(art)
                await db.commit()
                await db.refresh(art)
                break
                
    if not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactOut.model_validate(art)

@router.get("/preview", response_model=FilePreviewResponse)
async def preview_file(
    repo_name: str = Query(..., description="Repository name"),
    path: str = Query(..., description="Relative file path"),
    current_user: User = Depends(require_reader),
    db: AsyncSession = Depends(get_db)
):
    path = path.lstrip("/")
    
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    
    search_repos = [repo_name]
    if repo and repo.type.value == "group":
        search_repos = repo.member_repo_names or []
        
    target_repo_name = None
    for r_name in search_repos:
        if await storage_service.file_exists(r_name, path):
            target_repo_name = r_name
            break
            
    if not target_repo_name:
        raise HTTPException(status_code=404, detail="File not found")

    content_type, _ = mimetypes.guess_type(path)
    filename = os.path.basename(path)

    # Check if text file
    text_extensions = [".pom", ".xml", ".json", ".txt", ".md", ".yaml", ".yml", ".sha1", ".md5", ".sha256", ".properties", ".gradle"]
    is_text = any(filename.endswith(ext) for ext in text_extensions) or (content_type and "text" in content_type)

    raw_bytes = await storage_service.read_bytes(target_repo_name, path)
    
    if is_text:
        try:
            text_content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_content = raw_bytes.decode("latin-1")
            except Exception:
                text_content = "[Binary preview not available]"
                is_text = False
    else:
        text_content = f"[Binary file: {len(raw_bytes)} bytes. Click Download to save.]"

    return FilePreviewResponse(
        filename=filename,
        path=path,
        content_type=content_type or "application/octet-stream",
        size_bytes=len(raw_bytes),
        content=text_content,
        is_text=is_text
    )

@router.get("/download")
async def download_file(
    repo_name: str = Query(...),
    path: str = Query(...),
    current_user: User = Depends(require_reader),
    db: AsyncSession = Depends(get_db)
):
    path = path.lstrip("/")
    
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    
    search_repos = [repo_name]
    if repo and repo.type.value == "group":
        search_repos = repo.member_repo_names or []
        
    target_repo_name = None
    for r_name in search_repos:
        if await storage_service.file_exists(r_name, path):
            target_repo_name = r_name
            break
            
    if not target_repo_name:
        target_repo_name = repo_name
        
    return storage_service.create_streaming_response(target_repo_name, path)

@router.delete("/artifact")
async def delete_artifact_file(
    repo_name: str = Query(...),
    path: str = Query(...),
    admin: User = Depends(require_developer),
    db: AsyncSession = Depends(get_db)
):
    path = path.lstrip("/")
    
    stmt = select(Repository).where(Repository.name == repo_name)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    
    if repo and repo.type.value == "group":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete artifacts directly from a group repository. Please delete from the member repository."
        )
        
    deleted = await storage_service.delete_artifact(repo_name, path)
    
    # Remove from DB
    stmt = select(Artifact).where(Artifact.repo_name == repo_name, Artifact.path == path)
    res = await db.execute(stmt)
    art = res.scalar_one_or_none()
    if art:
        await db.delete(art)
        await db.commit()

    if not deleted and not art:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {"status": "success", "message": f"Artifact {path} deleted successfully"}
