from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import repository
from app.schemas import ControlCreate, ControlOut, ControlStatusUpdate


router = APIRouter(prefix="/controls", tags=["controls"])


@router.get("", response_model=list[ControlOut])
def get_controls() -> list[dict]:
    return repository.list_controls()


@router.get("/{control_db_id}", response_model=ControlOut)
def get_control(control_db_id: int) -> dict:
    row = repository.get_control(control_db_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Control not found")
    return row


@router.post("", response_model=ControlOut, status_code=201)
def post_control(payload: ControlCreate) -> dict:
    return repository.create_control(payload)


@router.patch("/{control_db_id}/status", response_model=ControlOut)
def patch_control_status(control_db_id: int, payload: ControlStatusUpdate) -> dict:
    row = repository.update_control_status(
        control_db_id=control_db_id, status=payload.implementation_status
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Control not found")
    return row
