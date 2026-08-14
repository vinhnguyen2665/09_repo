import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.repository import Repository, RepoFormat, RepoType
from app.api import (
    api_router,
    dispatcher_router,
    docker_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("zero9repo")

async def init_db_and_seed():
    """
    Creates tables and seeds default admin user and default repositories if not exist.
    """
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Seed Admin User
        stmt = select(User).where(User.username == settings.ADMIN_USERNAME)
        res = await db.execute(stmt)
        admin_user = res.scalar_one_or_none()
        if not admin_user:
            logger.info(f"Seeding default admin user '{settings.ADMIN_USERNAME}'...")
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
            await db.commit()

        # 2. Seed Default Repositories
        default_repos = [
            # Maven
            {
                "name": "maven-private",
                "format": RepoFormat.MAVEN,
                "type": RepoType.HOSTED,
                "description": "Internal private Maven/Gradle hosted releases and snapshots",
                "upstream_url": None,
                "member_repo_names": []
            },
            {
                "name": "maven-proxy",
                "format": RepoFormat.MAVEN,
                "type": RepoType.PROXY,
                "description": "Proxy cache for Maven Central",
                "upstream_url": settings.MAVEN_CENTRAL_URL,
                "cache_ttl_hours": 720,
                "member_repo_names": []
            },
            {
                "name": "maven-group",
                "format": RepoFormat.MAVEN,
                "type": RepoType.GROUP,
                "description": "Unified Maven Group combining private artifacts and Central proxy",
                "upstream_url": None,
                "member_repo_names": ["maven-private", "maven-proxy"]
            },
            # NPM
            {
                "name": "npm-private",
                "format": RepoFormat.NPM,
                "type": RepoType.HOSTED,
                "description": "Private internal NPM package registry",
                "upstream_url": None,
                "member_repo_names": []
            },
            {
                "name": "npm-proxy",
                "format": RepoFormat.NPM,
                "type": RepoType.PROXY,
                "description": "Proxy cache for upstream npmjs.org",
                "upstream_url": settings.NPM_REGISTRY_URL,
                "cache_ttl_hours": 720,
                "member_repo_names": []
            },
            {
                "name": "npm-group",
                "format": RepoFormat.NPM,
                "type": RepoType.GROUP,
                "description": "Unified NPM Group registry",
                "upstream_url": None,
                "member_repo_names": ["npm-private", "npm-proxy"]
            },
            # Docker
            {
                "name": "docker-private",
                "format": RepoFormat.DOCKER,
                "type": RepoType.HOSTED,
                "description": "Internal OCI & Docker Container Registry",
                "upstream_url": None,
                "member_repo_names": []
            },
            # PyPI
            {
                "name": "pypi-private",
                "format": RepoFormat.PYPI,
                "type": RepoType.HOSTED,
                "description": "Internal hosted Python PyPI packages",
                "upstream_url": None,
                "member_repo_names": []
            },
            {
                "name": "pypi-proxy",
                "format": RepoFormat.PYPI,
                "type": RepoType.PROXY,
                "description": "Proxy cache for PyPI.org Simple Index",
                "upstream_url": settings.PYPI_INDEX_URL,
                "cache_ttl_hours": 720,
                "member_repo_names": []
            },
            {
                "name": "pypi-group",
                "format": RepoFormat.PYPI,
                "type": RepoType.GROUP,
                "description": "Unified PyPI Group combining internal and upstream packages",
                "upstream_url": None,
                "member_repo_names": ["pypi-private", "pypi-proxy"]
            },
        ]

        for repo_info in default_repos:
            repo_stmt = select(Repository).where(Repository.name == repo_info["name"])
            repo_res = await db.execute(repo_stmt)
            if not repo_res.scalar_one_or_none():
                logger.info(f"Seeding default repository '{repo_info['name']}'...")
                repo_obj = Repository(
                    name=repo_info["name"],
                    format=repo_info["format"],
                    type=repo_info["type"],
                    description=repo_info["description"],
                    upstream_url=repo_info.get("upstream_url"),
                    cache_ttl_hours=repo_info.get("cache_ttl_hours", 720),
                    member_repo_names=repo_info.get("member_repo_names", [])
                )
                db.add(repo_obj)
        
        await db.commit()
    logger.info("Database and repositories initialization complete.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_and_seed()
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(docker_router)
app.include_router(dispatcher_router)

# Mount frontend static distribution if available
frontend_dist = Path("../frontend/dist").resolve()
if not frontend_dist.exists():
    frontend_dist = Path("./frontend/dist").resolve()

if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("v2") or full_path.startswith("repository"):
            return FileResponse(frontend_dist / "index.html")
        file_candidate = frontend_dist / full_path
        if file_candidate.exists() and file_candidate.is_file():
            return FileResponse(file_candidate)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs_url": "/docs",
            "api_v1": settings.API_V1_STR
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
