import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger("zero9repo.database")

if settings.is_sqlite:
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    # Server databases (PostgreSQL / MySQL): keep a connection pool and
    # verify connections before use so restarts of the DB server are survived.
    engine_kwargs = {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    **engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass


async def ensure_database_exists() -> None:
    """
    For PostgreSQL: create the target database (e.g. ``zero9repo``) if it does
    not exist yet, by connecting to the built-in ``postgres`` maintenance DB.
    No-op for SQLite (the file is created automatically).
    """
    if not settings.is_postgresql:
        return

    url = make_url(settings.DATABASE_URL)
    db_name = url.database
    if not db_name or db_name == "postgres":
        return

    admin_engine = create_async_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
    )
    try:
        async with admin_engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            if not exists:
                logger.info(f"Creating PostgreSQL database '{db_name}'...")
                safe_name = db_name.replace('"', '""')
                await conn.execute(text(f'CREATE DATABASE "{safe_name}"'))
    except Exception as exc:
        # The user may lack CREATEDB permission; the database may already exist.
        logger.warning(f"Could not verify/create database '{db_name}': {exc}")
    finally:
        await admin_engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
