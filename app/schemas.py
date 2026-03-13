from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ControlStatus = Literal["draft", "implemented", "needs_evidence", "in_review"]
EvidenceStatus = Literal[
    "accepted",
    "submitted",
    "approved",
    "pending",
    "rejected",
    "locked",
    "stale",
]
TaskStatus = Literal["open", "in_progress", "completed"]
TaskPriority = Literal["low", "medium", "high"]
AuditType = Literal["type1", "type2"]
AuditStatus = Literal["draft", "in_progress", "closed"]
FindingSeverity = Literal["low", "medium", "high", "critical"]
FindingStatus = Literal["open", "in_progress", "closed"]


class ControlCreate(BaseModel):
    control_id: str = Field(min_length=2, max_length=32)
    title: str = Field(min_length=3, max_length=140)
    description: str = Field(min_length=10)
    owner: Optional[str] = Field(default=None, max_length=120)
    implementation_status: ControlStatus = "draft"
    type1_ready: bool = False
    type2_ready: bool = False
    last_tested_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None


class ControlOut(BaseModel):
    id: int
    control_id: str
    title: str
    description: str
    owner: Optional[str]
    implementation_status: ControlStatus
    type1_ready: bool
    type2_ready: bool
    last_tested_at: Optional[str]
    next_review_at: Optional[str]


class ControlStatusUpdate(BaseModel):
    implementation_status: ControlStatus


class EvidenceCreate(BaseModel):
    control_id: int
    name: str = Field(min_length=3, max_length=180)
    source: str = Field(min_length=2, max_length=120)
    artifact_path: str = Field(min_length=3, max_length=260)
    collected_at: datetime
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    status: EvidenceStatus = "submitted"
    notes: Optional[str] = Field(default=None, max_length=1500)
    submitter_id: Optional[int] = None
    approver_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejected_reason: Optional[str] = Field(default=None, max_length=1500)
    locked_at: Optional[datetime] = None
    sha256_hash: Optional[str] = Field(default=None, min_length=64, max_length=64)
    sharepoint_id: Optional[str] = Field(default=None, max_length=255)
    audit_period_id: Optional[int] = None
    collection_due_date: Optional[datetime] = None


class EvidenceOut(BaseModel):
    id: int
    control_id: int
    name: str
    source: str
    artifact_path: str
    collected_at: str
    period_start: Optional[str]
    period_end: Optional[str]
    status: EvidenceStatus
    notes: Optional[str]
    submitter_id: Optional[int] = None
    approver_id: Optional[int] = None
    approved_at: Optional[str] = None
    rejected_reason: Optional[str] = None
    locked_at: Optional[str] = None
    sha256_hash: Optional[str] = None
    sharepoint_id: Optional[str] = None
    audit_period_id: Optional[int] = None
    collection_due_date: Optional[str] = None


class EvidenceRejectRequest(BaseModel):
    rejected_reason: str = Field(min_length=3, max_length=1500)


class AuditPeriodCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    period_start: datetime
    period_end: datetime
    type: AuditType


class AuditPeriodOut(BaseModel):
    id: int
    name: str
    period_start: str
    period_end: str
    type: AuditType
    created_by: Optional[int] = None
    created_at: str


class TaskCreate(BaseModel):
    type: str = Field(min_length=2, max_length=60)
    source_object_type: str = Field(min_length=2, max_length=60)
    source_object_id: int
    title: str = Field(min_length=3, max_length=180)
    description: Optional[str] = Field(default=None, max_length=1500)
    owner_id: int
    due_date: Optional[datetime] = None
    status: TaskStatus = "open"
    priority: TaskPriority = "medium"


class TaskUpdate(BaseModel):
    status: TaskStatus


class TaskOut(BaseModel):
    id: int
    type: str
    source_object_type: str
    source_object_id: int
    title: str
    description: Optional[str]
    owner_id: int
    due_date: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    created_at: str
    completed_at: Optional[str] = None


class AuditCreate(BaseModel):
    audit_period_id: int
    type: AuditType
    firm_name: str = Field(min_length=2, max_length=180)
    scope_notes: Optional[str] = Field(default=None, max_length=2000)


class AuditOut(BaseModel):
    id: int
    audit_period_id: int
    type: AuditType
    firm_name: str
    status: AuditStatus
    scope_notes: Optional[str]
    created_by: Optional[int] = None
    created_at: str
    closed_at: Optional[str] = None


class AuditFindingCreate(BaseModel):
    control_id: int
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=2000)
    severity: FindingSeverity
    owner_id: int
    due_date: Optional[datetime] = None


class AuditFindingUpdate(BaseModel):
    status: FindingStatus
    remediation_notes: Optional[str] = Field(default=None, max_length=2000)


class AuditFindingOut(BaseModel):
    id: int
    audit_id: int
    control_id: int
    title: str
    description: str
    severity: FindingSeverity
    status: FindingStatus
    owner_id: int
    due_date: Optional[str] = None
    closed_at: Optional[str] = None
    remediation_notes: Optional[str] = None


class ReadinessSummary(BaseModel):
    total_controls: int
    type1_ready_controls: int
    type2_ready_controls: int
    type1_readiness_percent: float
    type2_readiness_percent: float
    controls_missing_evidence: int


class GapItem(BaseModel):
    control_db_id: int
    control_id: str
    title: str
    reason: str


class Phase1Overview(BaseModel):
    soc2_progress_percent: float
    controls_passing: int
    controls_total: int
    policies_attention: int
    policies_ok: int
    policies_total: int
    tests_attention: int
    tests_ok: int
    tests_total: int
    vendors_attention: int
    vendors_ok: int
    vendors_total: int
    documents_attention: int
    documents_ok: int
    documents_total: int
