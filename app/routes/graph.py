from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import repository
from app.auth import get_current_user, require_role
from app.services import integrations


router = APIRouter(prefix="/graph", tags=["graph"])


class GraphRelationshipCreate(BaseModel):
    source_type: str = Field(min_length=2, max_length=40)
    source_key: str = Field(min_length=1, max_length=80)
    target_type: str = Field(min_length=2, max_length=40)
    target_key: str = Field(min_length=1, max_length=80)
    link_type: str | None = Field(default=None, min_length=2, max_length=60)


@router.get("/{object_type}")
def list_graph_objects(
    object_type: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    statuses = [status.__dict__ for status in integrations.get_statuses()]
    repository.sync_relationship_graph(statuses)
    return {"items": repository.list_graph_objects(object_type)}


@router.get("/{object_type}/{external_key}")
def get_graph_detail(
    object_type: str,
    external_key: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    statuses = [status.__dict__ for status in integrations.get_statuses()]
    repository.sync_relationship_graph(statuses)
    item = repository.get_graph_detail(object_type, external_key)
    if item is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return item


@router.get("/{object_type}/{external_key}/options")
def list_relationship_options(
    object_type: str,
    external_key: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    statuses = [status.__dict__ for status in integrations.get_statuses()]
    repository.sync_relationship_graph(statuses)
    item = repository.get_graph_detail(object_type, external_key)
    if item is None:
        raise HTTPException(status_code=404, detail="Object not found")
    return {"items": repository.list_graph_link_options(object_type)}


@router.post("/relationships")
def create_relationship(
    payload: GraphRelationshipCreate,
    current_user: dict[str, Any] = Depends(require_role("contributor")),
) -> dict[str, Any]:
    statuses = [status.__dict__ for status in integrations.get_statuses()]
    repository.sync_relationship_graph(statuses)
    try:
        detail = repository.create_graph_relationship(
            source_type=payload.source_type,
            source_key=payload.source_key,
            target_type=payload.target_type,
            target_key=payload.target_key,
            link_type=payload.link_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return detail


@router.delete("/relationships/{relationship_id}", status_code=204)
def delete_relationship(
    relationship_id: int,
    current_user: dict[str, Any] = Depends(require_role("contributor")),
) -> None:
    repository.delete_graph_relationship(relationship_id)
