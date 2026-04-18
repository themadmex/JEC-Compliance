from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str | None] = mapped_column(Text)
    source_object_type: Mapped[str | None] = mapped_column(Text)
    source_object_id: Mapped[int | None] = mapped_column(Integer)
    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id"))
    check_id: Mapped[int | None] = mapped_column(ForeignKey("control_checks.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[str | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="medium")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)
    completed_at: Mapped[str | None] = mapped_column(DateTime)
    resolved_at: Mapped[str | None] = mapped_column(DateTime)
