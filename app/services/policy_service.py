from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.compliance import Policy, PolicyConsistencyFlag, PolicyControl, PolicyVersion

logger = logging.getLogger(__name__)


def list_policies(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(Policy).order_by(Policy.title)).scalars().all()
    return [_policy_dict(p) for p in rows]


def get_policy(db: Session, policy_id: int) -> dict[str, Any] | None:
    p = db.get(Policy, policy_id)
    return _policy_dict(p) if p else None


def create_policy(db: Session, data: dict[str, Any], created_by: int | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    policy = Policy(
        framework_id=data.get("framework_id"),
        title=data["title"],
        description=data.get("description"),
        policy_type=data.get("policy_type"),
        owner_user_id=data.get("owner_user_id"),
        status="draft",
        review_frequency_days=data.get("review_frequency_days"),
        next_review_date=data.get("next_review_date"),
        version=data.get("version", "1.0"),
        created_at=now,
        updated_at=now,
    )
    db.add(policy)
    db.flush()
    return _policy_dict(policy)


def approve_policy(db: Session, policy_id: int, approver_id: int) -> dict[str, Any] | None:
    policy = db.get(Policy, policy_id)
    if policy is None:
        return None
    now = datetime.now(timezone.utc)
    policy.status = "approved"
    policy.last_approved_at = now
    policy.approved_by = approver_id
    policy.updated_at = now
    db.flush()
    return _policy_dict(policy)


def add_policy_version(
    db: Session, policy_id: int, data: dict[str, Any], uploaded_by: int | None
) -> dict[str, Any] | None:
    policy = db.get(Policy, policy_id)
    if policy is None:
        return None

    file_bytes: bytes | None = data.get("file_bytes")
    sha256 = hashlib.sha256(file_bytes).hexdigest() if file_bytes else None

    version_row = PolicyVersion(
        policy_id=policy_id,
        version=data.get("version"),
        uploaded_by=uploaded_by,
        sharepoint_item_id=data.get("sharepoint_item_id"),
        sha256_hash=sha256,
        change_summary=data.get("change_summary"),
    )
    db.add(version_row)

    # Update policy to needs_review if already approved
    if policy.status == "approved":
        policy.status = "needs_review"
    policy.version = data.get("version", policy.version)
    policy.sha256_hash = sha256 or policy.sha256_hash
    policy.updated_at = datetime.now(timezone.utc)
    db.flush()
    return _policy_dict(policy)


def list_policy_versions(db: Session, policy_id: int) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy_id)
            .order_by(PolicyVersion.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": v.id,
            "policy_id": v.policy_id,
            "version": v.version,
            "uploaded_by": v.uploaded_by,
            "sharepoint_item_id": v.sharepoint_item_id,
            "sha256_hash": v.sha256_hash,
            "change_summary": v.change_summary,
            "created_at": _fmt(v.created_at),
        }
        for v in rows
    ]


def list_policy_controls(db: Session, policy_id: int) -> list[int]:
    rows = (
        db.execute(select(PolicyControl).where(PolicyControl.policy_id == policy_id))
        .scalars()
        .all()
    )
    return [r.control_id for r in rows]


def link_policy_control(db: Session, policy_id: int, control_id: int) -> None:
    existing = db.execute(
        select(PolicyControl).where(
            PolicyControl.policy_id == policy_id, PolicyControl.control_id == control_id
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(PolicyControl(policy_id=policy_id, control_id=control_id))
        db.flush()


def run_consistency_scan(db: Session) -> int:
    """Detect policy issues and write policy_consistency_flags rows. Returns flags created."""
    today = date.today()
    policies = db.execute(select(Policy)).scalars().all()
    created = 0

    for policy in policies:
        # Flag overdue reviews
        if policy.next_review_date:
            nrd = _parse_date(str(policy.next_review_date))
            if nrd and nrd < today and policy.status not in ("retired",):
                _upsert_flag(
                    db,
                    policy_id=policy.id,
                    control_id=None,
                    flag_type="review_overdue",
                    severity="warning",
                    detail=f"Policy '{policy.title}' review was due {nrd}.",
                )
                created += 1

        # Flag approved policies not linked to any control
        if policy.status == "approved":
            linked = list_policy_controls(db, policy.id)
            if not linked:
                _upsert_flag(
                    db,
                    policy_id=policy.id,
                    control_id=None,
                    flag_type="unmapped_control_reference",
                    severity="warning",
                    detail=f"Approved policy '{policy.title}' is not linked to any control.",
                )
                created += 1

    db.flush()
    return created


def _upsert_flag(
    db: Session,
    *,
    policy_id: int,
    control_id: int | None,
    flag_type: str,
    severity: str,
    detail: str,
) -> None:
    existing = db.execute(
        select(PolicyConsistencyFlag).where(
            PolicyConsistencyFlag.policy_id == policy_id,
            PolicyConsistencyFlag.flag_type == flag_type,
            PolicyConsistencyFlag.is_active == True,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            PolicyConsistencyFlag(
                policy_id=policy_id,
                control_id=control_id,
                flag_type=flag_type,
                severity=severity,
                detail=detail,
                is_active=True,
            )
        )


def _policy_dict(p: Policy) -> dict[str, Any]:
    return {
        "id": p.id,
        "framework_id": p.framework_id,
        "title": p.title,
        "description": p.description,
        "policy_type": p.policy_type,
        "owner_user_id": p.owner_user_id,
        "status": p.status,
        "review_frequency_days": p.review_frequency_days,
        "last_approved_at": _fmt(p.last_approved_at),
        "next_review_date": str(p.next_review_date) if p.next_review_date else None,
        "approved_by": p.approved_by,
        "sharepoint_url": p.sharepoint_url,
        "file_name": p.file_name,
        "version": p.version,
        "created_at": _fmt(p.created_at),
        "updated_at": _fmt(p.updated_at),
    }


def _fmt(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        return None
