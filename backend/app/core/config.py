import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Zero9Repo"
    PROJECT_DESCRIPTION: str = "Production-Ready Lightweight Enterprise Repository Manager (Nexus/Artifactory Alternative)"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Server Host & Port
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    PUBLIC_URL: str = "http://localhost:8000"

    # Security
    SECRET_KEY: str = "zero9repo-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: Optional[int] = os.getenv("DB_PORT", 5432)
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "zero9repo")
    DATABASE_URL: Optional[str] = None

    @model_validator(mode="after")
    def compute_database_url(self) -> 'Settings':
        if not self.DATABASE_URL:
            if self.DB_TYPE == "sqlite":
                self.DATABASE_URL = "sqlite+aiosqlite:///./data/zero9repo.db"
            elif self.DB_TYPE == "postgresql":
                port = self.DB_PORT or 5432
                self.DATABASE_URL = f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{port}/{self.DB_NAME}"
            elif self.DB_TYPE == "mysql":
                port = self.DB_PORT or 3306
                self.DATABASE_URL = f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{port}/{self.DB_NAME}"
        return self

    # Storage Directory
    BASE_DATA_DIR: Path = Path("./data")
    STORAGE_DIR: Path = Path("./data/storage")
    CACHE_DIR: Path = Path("./data/cache")
    TEMP_DIR: Path = Path("./data/temp")

    # Default Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@zero9repo.io"

    # Upstream Proxy Default Configs
    MAVEN_CENTRAL_URL: str = "https://repo1.maven.org/maven2"
    NPM_REGISTRY_URL: str = "https://registry.npmjs.org"
    PYPI_INDEX_URL: str = "https://pypi.org"
    DEFAULT_CACHE_TTL_HOURS: int = 720  # 30 days


settings = Settings()

# Ensure directories exist
settings.BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
