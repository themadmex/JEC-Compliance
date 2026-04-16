from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CheckEvidence(Base):
    __tablename__ = "check_evidence"
    __table_args__ = (
        UniqueConstraint("check_id", "evidence_id", name="uq_check_evidence_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    check_id: Mapped[int] = mapped_column(
        ForeignKey("control_checks.id", ondelete="CASCADE"), nullable=False
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())


class AuditUser(Base):
    __tablename__ = "audit_users"
    __table_args__ = (
        UniqueConstraint("audit_id", "user_id", name="uq_audit_users_assignment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[int] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    access_expires_at: Mapped[str | None] = mapped_column(DateTime)


class AuditComment(Base):
    __tablename__ = "audit_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[int] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[int | None] = mapped_column(
        ForeignKey("audit_requests.id", ondelete="CASCADE")
    )
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("audit_comments.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)
