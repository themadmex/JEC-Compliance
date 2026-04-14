from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/jec_soc2.db")

# Setup for SQLite specifics (like foreign keys)
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# Create engine with pooling logic
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    # Use StaticPool for SQLite to keep the connection open in memory if needed
    poolclass=StaticPool if DATABASE_URL.startswith("sqlite") else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class _LegacyConnection:
    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def __enter__(self) -> "_LegacyConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()
        return False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)

def get_db_session() -> Session:
    """Dependency for FastAPI routes to get a DB session."""
    db = SessionLocal()
    try:
        if DATABASE_URL.startswith("sqlite"):
            db.execute(text("PRAGMA foreign_keys = ON;"))
        yield db
    finally:
        db.close()

def get_connection():
    """Legacy support for raw SQL execution during transition."""
    # This returns a raw DB-API connection from the engine.
    conn = engine.raw_connection()
    if DATABASE_URL.startswith("sqlite"):
        conn.driver_connection.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
    return _LegacyConnection(conn)

def init_db() -> None:
    """Initialize the schema using raw SQL (preserving the existing init_db logic)."""
    # Note: In a full Postgres migration, we would use Alembic for this.
    # For Milestone 1, we keep the existing raw SQL schema for compatibility.
    db_dir = Path("data")
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Use a one-off connection to run the bootstrap script
    from app.db_schema import BOOTSTRAP_SQL # We will move the SQL to a separate file
    
    with engine.connect() as conn:
        # Split by semicolon for Postgres compatibility if needed, 
        # but for now we use the existing sqlite executescript style
        for statement in BOOTSTRAP_SQL.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        conn.commit()
