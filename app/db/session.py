from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


DATABASE_URL = get_settings().database_url

connect_args: dict[str, object] = {}
engine_kwargs: dict[str, object] = {"future": True}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        if DATABASE_URL.startswith("sqlite"):
            db.execute(text("PRAGMA foreign_keys = ON;"))
        yield db
    finally:
        db.close()
