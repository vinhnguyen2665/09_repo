import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

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
    # DB_TYPE: "sqlite" (default) | "postgresql" (alias: "postgres") | "mysql"
    # Setting DATABASE_URL directly overrides every DB_* value below.
    DB_TYPE: str = "sqlite"
    DB_HOST: str = "localhost"
    DB_PORT: Optional[int] = None  # defaults: 5432 for PostgreSQL, 3306 for MySQL
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "zero9repo"
    DATABASE_URL: Optional[str] = None

    @model_validator(mode="after")
    def compute_database_url(self) -> 'Settings':
        db_type = (self.DB_TYPE or "sqlite").strip().lower()
        if db_type in ("postgres", "pg"):
            db_type = "postgresql"
        self.DB_TYPE = db_type

        if not self.DATABASE_URL:
            user = quote_plus(self.DB_USER)
            password = quote_plus(self.DB_PASSWORD)
            if db_type == "sqlite":
                self.DATABASE_URL = "sqlite+aiosqlite:///./data/zero9repo.db"
            elif db_type == "postgresql":
                port = self.DB_PORT or 5432
                self.DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{self.DB_HOST}:{port}/{self.DB_NAME}"
            elif db_type == "mysql":
                port = self.DB_PORT or 3306
                self.DATABASE_URL = f"mysql+aiomysql://{user}:{password}@{self.DB_HOST}:{port}/{self.DB_NAME}"
            else:
                raise ValueError(f"Unsupported DB_TYPE '{self.DB_TYPE}'. Use sqlite, postgresql or mysql.")
        elif self.DATABASE_URL.startswith(("postgresql://", "postgres://")):
            # Plain PostgreSQL URLs need the async driver prefix
            self.DATABASE_URL = "postgresql+asyncpg://" + self.DATABASE_URL.split("://", 1)[1]
        return self

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

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
