from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ControlCheck(Base):
    __tablename__ = "control_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)
    checked_at: Mapped[str | None] = mapped_column(DateTime)
    result: Mapped[str | None] = mapped_column(Text)
    details: Mapped[str | None] = mapped_column(Text)
    check_name: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    result_detail: Mapped[str | None] = mapped_column(Text)
    run_at: Mapped[str | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    triggered_by: Mapped[str | None] = mapped_column(Text)
    created_task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
