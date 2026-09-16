"""Database wiring.

SQLite is the development default. The only Postgres-specific change needed
later is DATABASE_URL — `connect_args` is applied for SQLite only, and no
SQLite-specific column types are used anywhere in app/models.py.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    # FastAPI serves requests from a threadpool, so a SQLite connection may be
    # touched by more than one thread over its lifetime.
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables on first run. Swap for Alembic when schemas start changing."""
    from app import models  # noqa: F401  (import registers the models)

    Base.metadata.create_all(bind=engine)
