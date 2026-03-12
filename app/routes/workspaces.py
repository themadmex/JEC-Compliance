from __future__ import annotations

from fastapi import APIRouter

from app import repository
from app.services import integrations


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/documents")
def get_documents_workspace() -> dict:
    return repository.get_documents_workspace()


@router.get("/audits")
def get_audits_workspace() -> dict:
    return repository.get_audits_workspace()


@router.get("/risk")
def get_risk_workspace() -> dict:
    return repository.get_risk_workspace()


@router.get("/policies")
def get_policy_workspace() -> dict:
    return repository.get_policy_workspace()


@router.get("/vendors")
def get_vendor_workspace() -> dict:
    statuses = [status.__dict__ for status in integrations.get_statuses()]
    return repository.get_vendor_workspace(statuses)


@router.get("/trust")
def get_trust_workspace() -> dict:
    return repository.get_trust_workspace()
