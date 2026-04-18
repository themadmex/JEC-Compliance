"""Phase 6 hardening schema alignment.

Revision ID: 20260417_000004
Revises: 20260416_000003
Create Date: 2026-04-17 00:00:00
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "20260417_000004"
down_revision = "20260416_000003"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "users" not in tables:
        return

    columns = _columns("users")
    if "scoped_token" not in columns:
        bind.exec_driver_sql("ALTER TABLE users ADD COLUMN scoped_token TEXT")
    if "token_expires_at" not in columns:
        bind.exec_driver_sql("ALTER TABLE users ADD COLUMN token_expires_at TEXT")

    if bind.dialect.name == "postgresql":
        bind.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_scoped_token ON users(scoped_token)"
        )
    else:
        bind.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_scoped_token ON users(scoped_token)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP INDEX IF EXISTS uq_users_scoped_token")

