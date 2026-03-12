from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


ControlStatus = Literal["draft", "implemented", "needs_evidence", "in_review"]
EvidenceStatus = Literal["accepted", "pending", "rejected", "stale"]


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
    status: EvidenceStatus = "accepted"
    notes: Optional[str] = Field(default=None, max_length=1500)


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
