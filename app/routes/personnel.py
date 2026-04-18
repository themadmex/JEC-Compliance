from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_role
from app.db.session import get_db_session
from app.services import personnel_service

router = APIRouter(prefix="/api/v1/personnel", tags=["personnel"])


class PersonnelCreate(BaseModel):
    email: str
    display_name: str | None = None
    department: str | None = None
    title: str | None = None
    employment_status: str = "active"
    start_date: str | None = None
    entra_oid: str | None = None
    user_id: int | None = None


class PersonnelUpdate(BaseModel):
    display_name: str | None = None
    department: str | None = None
    title: str | None = None
    employment_status: str | None = None
    termination_date: str | None = None


class RequirementCreate(BaseModel):
    title: str
    requirement_type: str = "training"
    applies_to: str = "all"
    due_within_days_of_hire: int | None = None
    recurrence_days: int | None = None
    control_id: int | None = None


class CompletionUpdate(BaseModel):
    evidence_url: str | None = None
    notes: str | None = None


@router.get("", response_model=list[dict])
def list_personnel(
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return personnel_service.list_personnel(db)


@router.get("/requirements", response_model=list[dict])
def list_requirements(
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    return personnel_service.list_requirements(db)


@router.post("", response_model=dict, status_code=201)
def create_person(
    payload: PersonnelCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    person = personnel_service.create_person(db, payload.model_dump())
    db.commit()
    return person


@router.patch("/{person_id}", response_model=dict)
def update_person(
    person_id: int,
    payload: PersonnelUpdate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    result = personnel_service.update_person(db, person_id, payload.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    db.commit()
    return result


@router.post("/requirements", response_model=dict, status_code=201)
def create_requirement(
    payload: RequirementCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    req = personnel_service.create_requirement(db, payload.model_dump())
    db.commit()
    return req


@router.get("/{person_id}", response_model=dict)
def get_person(
    person_id: int,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    person = personnel_service.get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.patch("/{person_id}/requirements/{req_id}", response_model=dict)
def mark_completed(
    person_id: int,
    req_id: int,
    payload: CompletionUpdate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
    db: Session = Depends(get_db_session),
) -> dict:
    result = personnel_service.mark_completed(
        db,
        person_id,
        req_id,
        evidence_url=payload.evidence_url,
        notes=payload.notes,
        completed_by=current_user["id"],
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Compliance record not found")
    db.commit()
    return result
