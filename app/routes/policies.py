from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db.session import get_db_session
from app.services import policy_service

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


class PolicyCreate(BaseModel):
    title: str
    description: str | None = None
    policy_type: str | None = None
    framework_id: int | None = None
    owner_user_id: int | None = None
    review_frequency_days: int | None = None
    next_review_date: str | None = None
    version: str | None = "1.0"


class PolicyVersionCreate(BaseModel):
    version: str | None = None
    change_summary: str | None = None
    sharepoint_item_id: str | None = None


class PolicyControlLink(BaseModel):
    control_id: int


@router.get("", response_model=list[dict])
def list_policies(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return policy_service.list_policies(db)


@router.get("/{policy_id}", response_model=dict)
def get_policy(
    policy_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> dict:
    policy = policy_service.get_policy(db, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("", response_model=dict, status_code=201)
def create_policy(
    payload: PolicyCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    policy = policy_service.create_policy(db, payload.model_dump(), created_by=current_user["id"])
    db.commit()
    return policy


@router.patch("/{policy_id}/approve", response_model=dict)
def approve_policy(
    policy_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    policy = policy_service.approve_policy(db, policy_id, approver_id=current_user["id"])
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.commit()
    return policy


@router.post("/{policy_id}/version", response_model=dict, status_code=201)
def add_policy_version(
    policy_id: int,
    payload: PolicyVersionCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    result = policy_service.add_policy_version(
        db, policy_id, payload.model_dump(), uploaded_by=current_user["id"]
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.commit()
    return result


@router.get("/{policy_id}/versions", response_model=list[dict])
def list_versions(
    policy_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return policy_service.list_policy_versions(db, policy_id)


@router.get("/{policy_id}/controls", response_model=list[int])
def get_policy_controls(
    policy_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> list[int]:
    if policy_service.get_policy(db, policy_id) is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy_service.list_policy_controls(db, policy_id)


@router.post("/{policy_id}/controls", status_code=204)
def link_control(
    policy_id: int,
    payload: PolicyControlLink,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> None:
    if policy_service.get_policy(db, policy_id) is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy_service.link_policy_control(db, policy_id, payload.control_id)
    db.commit()
