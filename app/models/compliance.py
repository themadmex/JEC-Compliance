from __future__ import annotations

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EvidenceControl(Base):
    __tablename__ = "evidence_controls"
    __table_args__ = (
        UniqueConstraint("evidence_id", "control_id", name="uq_evidence_controls_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mapped_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    framework_id: Mapped[int | None] = mapped_column(ForeignKey("frameworks.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    policy_type: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    review_frequency_days: Mapped[int | None] = mapped_column(Integer)
    last_approved_at: Mapped[str | None] = mapped_column(DateTime)
    next_review_date: Mapped[str | None] = mapped_column(Date)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sharepoint_url: Mapped[str | None] = mapped_column(Text)
    sharepoint_item_id: Mapped[str | None] = mapped_column(Text)
    local_path: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(Text)
    sha256_hash: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


class PolicyControl(Base):
    __tablename__ = "policy_controls"
    __table_args__ = (
        UniqueConstraint("policy_id", "control_id", name="uq_policy_controls_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    sharepoint_item_id: Mapped[str | None] = mapped_column(Text)
    sha256_hash: Mapped[str | None] = mapped_column(Text)
    change_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())


class PolicyConsistencyFlag(Base):
    __tablename__ = "policy_consistency_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy_id: Mapped[int] = mapped_column(
        ForeignKey("policies.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id"))
    flag_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[str | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AccessReview(Base):
    __tablename__ = "access_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    system_name: Mapped[str] = mapped_column(Text, nullable=False)
    integration_name: Mapped[str | None] = mapped_column(Text)
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    due_date: Mapped[str | None] = mapped_column(Date)
    completed_at: Mapped[str | None] = mapped_column(DateTime)
    period_start: Mapped[str | None] = mapped_column(Date)
    period_end: Mapped[str | None] = mapped_column(Date)
    total_accounts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accounts_approved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accounts_revoked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accounts_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


class AccessReviewAccount(Base):
    __tablename__ = "access_review_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        ForeignKey("access_reviews.id", ondelete="CASCADE"), nullable=False
    )
    external_user_id: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    role_in_system: Mapped[str | None] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    employment_status: Mapped[str | None] = mapped_column(Text)
    risk_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    decision: Mapped[str | None] = mapped_column(Text)
    decision_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decision_at: Mapped[str | None] = mapped_column(DateTime)
    decision_notes: Mapped[str | None] = mapped_column(Text)
    remediation_task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))


class Personnel(Base):
    __tablename__ = "personnel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    employment_status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    start_date: Mapped[str | None] = mapped_column(Date)
    termination_date: Mapped[str | None] = mapped_column(Date)
    entra_oid: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


class PersonnelRequirement(Base):
    __tablename__ = "personnel_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[str | None] = mapped_column(Text)
    applies_to: Mapped[str | None] = mapped_column(Text)
    due_within_days_of_hire: Mapped[int | None] = mapped_column(Integer)
    recurrence_days: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    control_id: Mapped[int | None] = mapped_column(ForeignKey("controls.id"))


class PersonnelComplianceRecord(Base):
    __tablename__ = "personnel_compliance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    personnel_id: Mapped[int] = mapped_column(
        ForeignKey("personnel.id", ondelete="CASCADE"), nullable=False
    )
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("personnel_requirements.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    completed_at: Mapped[str | None] = mapped_column(DateTime)
    due_date: Mapped[str | None] = mapped_column(Date)
    evidence_url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    likelihood: Mapped[int | None] = mapped_column(Integer)
    impact: Mapped[int | None] = mapped_column(Integer)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    inherent_risk_score: Mapped[int | None] = mapped_column(Integer)
    residual_risk_score: Mapped[int | None] = mapped_column(Integer)
    treatment: Mapped[str | None] = mapped_column(Text)
    treatment_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    review_date: Mapped[str | None] = mapped_column(Date)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[str | None] = mapped_column(DateTime)


class RiskControl(Base):
    __tablename__ = "risk_controls"
    __table_args__ = (
        UniqueConstraint("risk_id", "control_id", name="uq_risk_controls_pair"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)
    control_id: Mapped[int] = mapped_column(ForeignKey("controls.id"), nullable=False)


class RiskHistory(Base):
    __tablename__ = "risk_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_id: Mapped[int] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)
    likelihood: Mapped[int | None] = mapped_column(Integer)
    impact: Mapped[int | None] = mapped_column(Integer)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    recorded_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)
