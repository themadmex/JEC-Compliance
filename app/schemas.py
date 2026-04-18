from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ControlStatus = Literal["draft", "implemented", "needs_evidence", "in_review"]
EvidenceStatus = Literal[
    "submitted",
    "accepted",
    "rejected",
    "locked",
    "stale",
    "expired",
    "flagged",
    "not_applicable",
]
TaskStatus = Literal["open", "in_progress", "completed"]
TaskPriority = Literal["low", "medium", "high"]
AuditType = Literal["type1", "type2"]
AuditStatus = Literal["preparation", "in_progress", "fieldwork", "review", "completed", "cancelled"]
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
    title: str = Field(min_length=3, max_length=180)
    description: Optional[str] = Field(default=None, max_length=1500)
    source_type: str = Field(min_length=2, max_length=120)  # manual, integration, policy, system_generated
    status: EvidenceStatus = "submitted"
    uploaded_by: Optional[int] = None
    reviewed_by: Optional[int] = None
    rejection_reason: Optional[str] = Field(default=None, max_length=1500)
    valid_from: datetime
    valid_to: Optional[datetime] = None
    sha256_hash: Optional[str] = Field(default=None, min_length=64, max_length=64)
    sharepoint_url: Optional[str] = Field(default=None, max_length=1000)
    sharepoint_item_id: Optional[str] = Field(default=None, max_length=255)
    local_path: Optional[str] = Field(default=None, max_length=1000)
    file_name: str = Field(min_length=1, max_length=255)
    file_size_bytes: int = Field(gt=0)
    mime_type: Optional[str] = Field(default=None, max_length=120)
    locked_at: Optional[datetime] = None
    locked_by: Optional[int] = None
    audit_period_id: Optional[int] = None
    collection_due_date: Optional[datetime] = None


class EvidenceOut(BaseModel):
    id: int
    control_id: int
    title: str
    description: Optional[str]
    source_type: str
    status: EvidenceStatus
    uploaded_by: Optional[int] = None
    reviewed_by: Optional[int] = None
    rejection_reason: Optional[str] = None
    valid_from: str
    valid_to: Optional[str] = None
    sha256_hash: Optional[str] = None
    sharepoint_url: Optional[str] = None
    sharepoint_item_id: Optional[str] = None
    local_path: Optional[str] = None
    file_name: str
    file_size_bytes: int
    mime_type: Optional[str] = None
    locked_at: Optional[str] = None
    locked_by: Optional[int] = None
    audit_period_id: Optional[int] = None
    collection_due_date: Optional[str] = None
    created_at: str
    updated_at: str


class EvidenceRejectRequest(BaseModel):
    rejected_reason: str = Field(min_length=3, max_length=1500)


class AuditPeriodCreate(BaseModel):
    framework_id: int = 1
    name: str = Field(min_length=2, max_length=120)
    report_type: AuditType
    point_in_time_date: Optional[datetime] = None
    observation_start: Optional[datetime] = None
    observation_end: Optional[datetime] = None


class AuditPeriodOut(BaseModel):
    id: int
    framework_id: Optional[int] = None
    name: str
    report_type: AuditType
    point_in_time_date: Optional[str] = None
    observation_start: Optional[str] = None
    observation_end: Optional[str] = None
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
    period_id: int
    audit_firm: str = Field(min_length=2, max_length=180)
    early_access_date: Optional[datetime] = None
    fieldwork_start: datetime
    fieldwork_end: datetime
    notes: Optional[str] = Field(default=None, max_length=2000)


class AuditOut(BaseModel):
    id: int
    period_id: int
    audit_firm: str
    status: AuditStatus
    early_access_date: Optional[str] = None
    fieldwork_start: Optional[str] = None
    fieldwork_end: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[int] = None
    created_at: str
    closed_at: Optional[str] = None


class AuditUpdate(BaseModel):
    status: Optional[AuditStatus] = None
    early_access_date: Optional[datetime] = None
    fieldwork_start: Optional[datetime] = None
    fieldwork_end: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class AuditControlUpdate(BaseModel):
    in_scope: Optional[bool] = None
    auditor_notes: Optional[str] = Field(default=None, max_length=2000)


class AuditorAssignmentCreate(BaseModel):
    user_id: int
    access_expires_at: Optional[datetime] = None


class AuditRequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    description: Optional[str] = Field(default=None, max_length=2000)
    control_id: Optional[int] = None
    request_type: str = Field(default="evidence_request", min_length=3, max_length=60)
    sample_size: Optional[int] = Field(default=None, ge=1)
    due_date: Optional[datetime] = None


class AuditRequestUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=40)
    assigned_to: Optional[int] = None


class AuditRequestEvidenceCreate(BaseModel):
    evidence_id: int


class AuditCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    is_internal: bool = False
    parent_id: Optional[int] = None


class AuditFindingCreate(BaseModel):
    control_id: Optional[int] = None
    finding_type: str = Field(default="exception", min_length=3, max_length=60)
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=2000)
    severity: FindingSeverity
    owner_id: Optional[int] = None
    due_date: Optional[datetime] = None


class AuditFindingUpdate(BaseModel):
    status: FindingStatus
    remediation_notes: Optional[str] = Field(default=None, max_length=2000)


class AuditFindingOut(BaseModel):
    id: int
    audit_id: int
    control_id: Optional[int]
    title: str
    description: Optional[str]
    severity: FindingSeverity
    status: FindingStatus
    owner_id: Optional[int]
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
