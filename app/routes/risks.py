from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db.session import get_db_session
from app.services import risk_service

router = APIRouter(prefix="/api/v1/risks", tags=["risks"])


class RiskCreate(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    owner_user_id: int | None = None
    likelihood: int | None = None
    impact: int | None = None
    residual_risk_score: int | None = None
    treatment: str | None = None
    treatment_notes: str | None = None
    status: str = "open"
    review_date: str | None = None


class RiskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    owner_user_id: int | None = None
    likelihood: int | None = None
    impact: int | None = None
    residual_risk_score: int | None = None
    treatment: str | None = None
    treatment_notes: str | None = None
    status: str | None = None
    review_date: str | None = None


class ReviewNote(BaseModel):
    notes: str | None = None


class ControlLink(BaseModel):
    control_id: int


class ExportRequest(BaseModel):
    format: str = "json"  # json | csv


@router.get("", response_model=list[dict])
def list_risks(
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return risk_service.list_risks(db)


@router.post("/export", response_class=Response)
def export_risks(
    payload: ExportRequest,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> Response:
    fmt = payload.format.lower()
    if fmt == "csv":
        content = risk_service.export_csv(db)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=risk_register.csv"},
        )
    content = risk_service.export_json(db)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=risk_register.json"},
    )


@router.get("/{risk_id}", response_model=dict)
def get_risk(
    risk_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> dict:
    risk = risk_service.get_risk(db, risk_id)
    if risk is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    return risk


@router.post("", response_model=dict, status_code=201)
def create_risk(
    payload: RiskCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    risk = risk_service.create_risk(db, payload.model_dump(), created_by=current_user["id"])
    db.commit()
    return risk


@router.patch("/{risk_id}", response_model=dict)
def update_risk(
    risk_id: int,
    payload: RiskUpdate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    result = risk_service.update_risk(db, risk_id, payload.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    db.commit()
    return result


@router.post("/{risk_id}/review", response_model=dict, status_code=201)
def record_review(
    risk_id: int,
    payload: ReviewNote,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    result = risk_service.record_review(db, risk_id, recorded_by=current_user["id"], notes=payload.notes)
    if result is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    db.commit()
    return result


@router.get("/{risk_id}/history", response_model=list[dict])
def get_history(
    risk_id: int,
    current_user: dict[str, Any] = Depends(require_role("viewer")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return risk_service.get_risk_history(db, risk_id)


@router.post("/{risk_id}/controls", status_code=204)
def link_control(
    risk_id: int,
    payload: ControlLink,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> None:
    if risk_service.get_risk(db, risk_id) is None:
        raise HTTPException(status_code=404, detail="Risk not found")
    risk_service.link_control(db, risk_id, payload.control_id)
    db.commit()
