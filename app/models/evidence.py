from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str | None] = mapped_column(Text)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    collected_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    period_start: Mapped[str | None] = mapped_column(DateTime)
    period_end: Mapped[str | None] = mapped_column(DateTime)
    valid_from: Mapped[str | None] = mapped_column(DateTime)
    valid_to: Mapped[str | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="submitted")
    notes: Mapped[str | None] = mapped_column(Text)
    submitter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[str | None] = mapped_column(DateTime)
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[str | None] = mapped_column(DateTime)
    locked_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sha256_hash: Mapped[str | None] = mapped_column(Text)
    sharepoint_id: Mapped[str | None] = mapped_column(Text)
    sharepoint_url: Mapped[str | None] = mapped_column(Text)
    sharepoint_item_id: Mapped[str | None] = mapped_column(Text)
    local_path: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(Text)
    audit_period_id: Mapped[int | None] = mapped_column(ForeignKey("audit_periods.id"))
    collection_due_date: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)
