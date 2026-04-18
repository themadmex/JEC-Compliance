from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db.session import get_db_session
from app.services import access_review_service

router = APIRouter(prefix="/api/v1/access-reviews", tags=["access-reviews"])


class AccessReviewCreate(BaseModel):
    title: str
    system_name: str
    integration_name: str | None = None
    reviewer_user_id: int | None = None
    due_date: str | None = None
    period_start: str | None = None
    period_end: str | None = None


class DecisionUpdate(BaseModel):
    decision: str  # approved | revoked
    notes: str | None = None


@router.get("", response_model=list[dict])
def list_reviews(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return access_review_service.list_reviews(db)


@router.get("/{review_id}", response_model=dict)
def get_review(
    review_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> dict:
    review = access_review_service.get_review(db, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Access review not found")
    return review


@router.post("", response_model=dict, status_code=201)
def create_review(
    payload: AccessReviewCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    review = access_review_service.create_review(db, payload.model_dump(), created_by=current_user["id"])
    db.commit()
    return review


@router.post("/{review_id}/start", response_model=dict)
def start_review(
    review_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    result = access_review_service.start_review(db, review_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Access review not found")
    db.commit()
    return result


@router.get("/{review_id}/accounts", response_model=list[dict])
def list_accounts(
    review_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return access_review_service.list_accounts(db, review_id)


@router.patch("/{review_id}/accounts/{account_id}", response_model=dict)
def record_decision(
    review_id: int,
    account_id: int,
    payload: DecisionUpdate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    valid = {"approved", "revoked", "pending"}
    if payload.decision not in valid:
        raise HTTPException(status_code=422, detail=f"decision must be one of {valid}")
    result = access_review_service.record_decision(
        db, review_id, account_id, payload.decision, current_user["id"], payload.notes
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found in this review")
    db.commit()
    return result


@router.post("/{review_id}/complete", response_model=dict)
def complete_review(
    review_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    result = access_review_service.complete_review(db, review_id, completed_by=current_user["id"])
    if result is None:
        raise HTTPException(status_code=404, detail="Access review not found")
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    db.commit()
    return result
