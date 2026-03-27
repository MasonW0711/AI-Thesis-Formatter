from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
Base = declarative_base()


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    # Import here to avoid circular import.
    from app.models import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Enable WAL mode after tables are created.
    # This runs after ensure_directories() has been called, avoiding import-order issues.
    # Gracefully skip on ephemeral filesystems (e.g. Streamlit Cloud free tier).
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.commit()
    except Exception:
        pass  # WAL not supported on this filesystem; fall back to default mode
