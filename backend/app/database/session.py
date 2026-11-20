"""SQLAlchemy engine / session management (SQLite)."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("database")


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)


def init_engine(url: str | None = None) -> Engine:
    """Create (or re-create) the engine. Tests call this with a temporary database."""
    global _engine
    url = url or get_settings().database_url
    _ensure_sqlite_dir(url)
    _engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)

    @event.listens_for(_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # pragma: no cover - trivial
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SessionLocal.configure(bind=_engine)
    return _engine


def get_engine() -> Engine:
    return _engine or init_engine()


def create_tables() -> None:
    from app import models  # noqa: F401  (registers ORM classes)

    Base.metadata.create_all(get_engine())
    log.info("Database ready (%s)", get_engine().url.render_as_string(hide_password=True))


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for background jobs."""
    get_engine()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
