from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import repository
from app.auth import require_role
from app.schemas import TaskCreate, TaskOut, TaskUpdate


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
def get_tasks(
    owner_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None, alias="type"),
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[dict]:
    return repository.list_tasks(owner_id=owner_id, status=status_filter, task_type=task_type)


@router.post("", response_model=TaskOut, status_code=201)
def post_task(
    payload: TaskCreate,
    current_user: dict[str, Any] = Depends(require_role("compliance_manager")),
) -> dict:
    task = repository.create_task(payload)
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="create",
        object_type="task",
        object_id=task["id"],
        previous_state=None,
        new_state=task,
    )
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def patch_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: dict[str, Any] = Depends(require_role("contributor")),
) -> dict:
    existing = repository.get_task(task_id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if current_user["role"] != "admin" and existing["owner_id"] != current_user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    updated = repository.update_task_status(task_id, payload.status)
    repository.log_audit_event(
        actor_id=current_user["id"],
        action="update",
        object_type="task",
        object_id=task_id,
        previous_state=existing,
        new_state=updated,
    )
    return updated
