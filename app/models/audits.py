from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditPeriod(Base):
    __tablename__ = "audit_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[str | None] = mapped_column(DateTime)
    period_end: Mapped[str | None] = mapped_column(DateTime)
    type: Mapped[str | None] = mapped_column(Text)
    report_type: Mapped[str | None] = mapped_column(Text)
    observation_start: Mapped[str | None] = mapped_column(DateTime)
    observation_end: Mapped[str | None] = mapped_column(DateTime)
    point_in_time_date: Mapped[str | None] = mapped_column(DateTime)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_period_id: Mapped[int | None] = mapped_column(ForeignKey("audit_periods.id"))
    period_id: Mapped[int | None] = mapped_column(ForeignKey("audit_periods.id"))
    type: Mapped[str | None] = mapped_column(Text)
    firm_name: Mapped[str | None] = mapped_column(Text)
    audit_firm: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="preparation")
    scope_notes: Mapped[str | None] = mapped_column(Text)
    early_access_date: Mapped[str | None] = mapped_column(DateTime)
    fieldwork_start: Mapped[str | None] = mapped_column(DateTime)
    fieldwork_end: Mapped[str | None] = mapped_column(DateTime)
    report_date: Mapped[str | None] = mapped_column(DateTime)
    lead_auditor_email: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)
    closed_at: Mapped[str | None] = mapped_column(DateTime)


class AuditControl(Base):
    __tablename__ = "audit_controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)
    evidence_status: Mapped[str | None] = mapped_column(Text, default="missing")
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    in_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auditor_notes: Mapped[str | None] = mapped_column(Text)


class AuditRequest(Base):
    __tablename__ = "audit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False)
    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id"))
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    request_type: Mapped[str | None] = mapped_column(Text, default="evidence_request")
    sample_size: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    due_date: Mapped[str | None] = mapped_column(DateTime)
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


class AuditRequestEvidence(Base):
    __tablename__ = "audit_request_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("audit_requests.id"), nullable=False)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"), nullable=False)
    attached_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    attached_at: Mapped[str | None] = mapped_column(DateTime)


class AuditFinding(Base):
    __tablename__ = "audit_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), nullable=False)
    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id"))
    finding_type: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    management_response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    due_date: Mapped[str | None] = mapped_column(DateTime)
    closed_at: Mapped[str | None] = mapped_column(DateTime)
    remediation_notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


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
