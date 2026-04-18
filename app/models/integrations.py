from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IntegrationRun(Base):
    __tablename__ = "integration_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str | None] = mapped_column(Text)
    integration_name: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[str | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    records_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class IntegrationSnapshot(Base):
    __tablename__ = "integration_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("integration_runs.id"))
    source: Mapped[str | None] = mapped_column(Text)
    snapshot_type: Mapped[str | None] = mapped_column(Text)
    data_json: Mapped[str | None] = mapped_column(Text)
    integration_name: Mapped[str | None] = mapped_column(Text)
    resource_type: Mapped[str | None] = mapped_column(Text)
    resource_id: Mapped[str | None] = mapped_column(Text)
    data: Mapped[str | None] = mapped_column(Text)
    is_service_account_candidate: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    service_account_reason: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    captured_at: Mapped[str | None] = mapped_column(DateTime)
