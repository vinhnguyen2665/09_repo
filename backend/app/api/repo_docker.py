from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import authenticate_user_from_request
from app.models.user import UserRole
from app.services.docker_engine import docker_engine
from app.core.config import settings

router = APIRouter(prefix="/v2", tags=["Docker / OCI Registry"])

@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
async def docker_v2_ping(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Docker V2 API check. Standard `docker login` ping.
    """
    user = await authenticate_user_from_request(request, db)
    if not user:
        return Response(
            status_code=401,
            headers={
                "WWW-Authenticate": 'Basic realm="Zero9Repo Registry"',
                "Docker-Distribution-API-Version": "registry/2.0",
                "Content-Type": "application/json"
            },
            content='{"errors":[{"code":"UNAUTHORIZED","message":"authentication required"}]}'
        )
    return Response(
        status_code=200,
        headers={"Docker-Distribution-API-Version": "registry/2.0"},
        content="{}"
    )

# 1. Blob Upload Initiate (POST)
@router.post("/{name:path}/blobs/uploads/")
@router.post("/{name:path}/blobs/uploads")
async def initiate_blob_upload(
    name: str,
    request: Request,
    digest: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="Zero9Repo Registry"'}
        )
    if user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer role required to push images")

    async def stream_gen():
        async for chunk in request.stream():
            yield chunk

    return await docker_engine.initiate_blob_upload(
        db=db,
        name=name,
        digest=digest,
        stream=stream_gen() if digest else None,
        public_url=str(request.base_url)
    )

# 2. Blob Upload Chunk (PATCH)
@router.patch("/{name:path}/blobs/uploads/{upload_uuid}")
async def patch_blob_upload(
    name: str,
    upload_uuid: str,
    request: Request
):
    async def stream_gen():
        async for chunk in request.stream():
            yield chunk

    return await docker_engine.patch_blob_upload(name, upload_uuid, stream_gen())

# 3. Blob Upload Complete (PUT)
@router.put("/{name:path}/blobs/uploads/{upload_uuid}")
async def complete_blob_upload(
    name: str,
    upload_uuid: str,
    request: Request,
    digest: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    async def stream_gen():
        async for chunk in request.stream():
            yield chunk

    return await docker_engine.complete_blob_upload(
        db=db,
        name=name,
        upload_uuid=upload_uuid,
        digest=digest,
        stream=stream_gen()
    )

# 4. Blob Get / Check (GET & HEAD)
@router.get("/{name:path}/blobs/{digest}")
async def get_blob(name: str, digest: str, db: AsyncSession = Depends(get_db)):
    return await docker_engine.get_blob(db, name, digest, is_head=False)

@router.head("/{name:path}/blobs/{digest}")
async def head_blob(name: str, digest: str, db: AsyncSession = Depends(get_db)):
    return await docker_engine.get_blob(db, name, digest, is_head=True)

# 5. Manifest Upload (PUT)
@router.put("/{name:path}/manifests/{reference}")
async def put_manifest(
    name: str,
    reference: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user_from_request(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Basic realm="Zero9Repo Registry"'}
        )
    if user.role not in [UserRole.ADMIN, UserRole.DEVELOPER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Developer role required to push images")

    body_bytes = await request.body()
    content_type = request.headers.get("content-type", "application/vnd.docker.distribution.manifest.v2+json")
    return await docker_engine.put_manifest(db, name, reference, body_bytes, content_type)

# 6. Manifest Get / Check (GET & HEAD)
@router.get("/{name:path}/manifests/{reference}")
async def get_manifest(name: str, reference: str, db: AsyncSession = Depends(get_db)):
    return await docker_engine.get_manifest(db, name, reference, is_head=False)

@router.head("/{name:path}/manifests/{reference}")
async def head_manifest(name: str, reference: str, db: AsyncSession = Depends(get_db)):
    return await docker_engine.get_manifest(db, name, reference, is_head=True)

# 7. List Tags
@router.get("/{name:path}/tags/list")
async def list_tags(name: str, db: AsyncSession = Depends(get_db)):
    return await docker_engine.list_tags(db, name)
