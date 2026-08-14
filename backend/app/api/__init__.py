from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.repositories import router as repos_router
from app.api.explorer import router as explorer_router
from app.api.stats import router as stats_router
from app.api.repo_dispatcher import router as dispatcher_router
from app.api.repo_docker import router as docker_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(repos_router)
api_router.include_router(explorer_router)
api_router.include_router(stats_router)

__all__ = [
    "api_router",
    "dispatcher_router",
    "docker_router",
]
