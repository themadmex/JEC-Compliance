from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReadinessSnapshot(Base):
    __tablename__ = "readiness_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_period_id: Mapped[int] = mapped_column(
        ForeignKey("audit_periods.id", ondelete="CASCADE"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(Text, nullable=False)
    calculated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    calculated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    controls_ready: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    controls_partial: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    controls_not_ready: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    controls_not_applicable: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


class ReadinessGap(Base):
    __tablename__ = "readiness_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("readiness_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)
    gap_type: Mapped[str] = mapped_column(Text, nullable=False)
    gap_start: Mapped[str | None] = mapped_column(Date)
    gap_end: Mapped[str | None] = mapped_column(Date)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
