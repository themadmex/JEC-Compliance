from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Framework(Base):
    __tablename__ = "frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())


class Control(Base):
    __tablename__ = "controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("frameworks.id"), nullable=False)
    control_id: Mapped[str] = mapped_column(Text, nullable=False)
    control_code: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    implementation_status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    frequency: Mapped[str | None] = mapped_column(Text)
    is_automated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    type1_ready: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type2_ready: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type1_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_started")
    type2_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_started")
    last_tested_at: Mapped[str | None] = mapped_column(DateTime)
    next_review_at: Mapped[str | None] = mapped_column(DateTime)
    next_review_date: Mapped[str | None] = mapped_column(DateTime)
    evidence_requirements: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)
