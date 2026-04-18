from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compliance import AccessReview, AccessReviewAccount, Personnel
from app.models.integrations import IntegrationSnapshot
from app.models.tasks import Task

logger = logging.getLogger(__name__)


def list_reviews(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(AccessReview).order_by(AccessReview.created_at.desc())).scalars().all()
    return [_review_dict(r) for r in rows]


def get_review(db: Session, review_id: int) -> dict[str, Any] | None:
    r = db.get(AccessReview, review_id)
    return _review_dict(r) if r else None


def create_review(db: Session, data: dict[str, Any], created_by: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    review = AccessReview(
        title=data["title"],
        system_name=data["system_name"],
        integration_name=data.get("integration_name"),
        reviewer_user_id=data.get("reviewer_user_id"),
        assigned_by=created_by,
        due_date=data.get("due_date"),
        period_start=data.get("period_start"),
        period_end=data.get("period_end"),
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(review)
    db.flush()
    return _review_dict(review)


def start_review(db: Session, review_id: int) -> dict[str, Any] | None:
    """Populate access_review_accounts from the latest integration snapshot for the system."""
    review = db.get(AccessReview, review_id)
    if review is None:
        return None

    # Fetch latest integration snapshot for the integration
    integration_name = review.integration_name
    accounts: list[dict[str, Any]] = []

    if integration_name:
        snapshot = (
            db.execute(
                select(IntegrationSnapshot)
                .where(
                    IntegrationSnapshot.integration_name == integration_name,
                    IntegrationSnapshot.resource_type == "user",
                )
                .order_by(IntegrationSnapshot.captured_at.desc())
            )
            .scalars()
            .first()
        )
        if snapshot and snapshot.data:
            try:
                user_data = json.loads(snapshot.data)
                accounts = [user_data] if isinstance(user_data, dict) else user_data
            except json.JSONDecodeError:
                pass

    # Get all personnel for risk flagging
    personnel_map: dict[str, str] = {}
    for p in db.execute(select(Personnel)).scalars().all():
        personnel_map[p.email.lower()] = p.employment_status

    review.status = "in_progress"
    review.total_accounts = len(accounts)
    review.accounts_pending = len(accounts)
    review.accounts_approved = 0
    review.accounts_revoked = 0
    review.updated_at = datetime.now(timezone.utc)

    for acct in accounts:
        email = (acct.get("email") or "").lower()
        emp_status = personnel_map.get(email, "unknown")
        risk_flag = emp_status in ("terminated", "department_changed")

        db.add(
            AccessReviewAccount(
                review_id=review_id,
                external_user_id=acct.get("id") or acct.get("user_id"),
                email=acct.get("email"),
                display_name=acct.get("display_name"),
                role_in_system=acct.get("role"),
                is_admin=bool(acct.get("is_admin") or acct.get("admin")),
                employment_status=emp_status,
                risk_flag=risk_flag,
                decision="pending",
            )
        )

    db.flush()
    return _review_dict(review)


def record_decision(
    db: Session,
    review_id: int,
    account_id: int,
    decision: str,
    decision_by: int,
    notes: str | None = None,
) -> dict[str, Any] | None:
    account = db.execute(
        select(AccessReviewAccount).where(
            AccessReviewAccount.id == account_id,
            AccessReviewAccount.review_id == review_id,
        )
    ).scalar_one_or_none()

    if account is None:
        return None

    previous_decision = account.decision
    account.decision = decision
    account.decision_by = decision_by
    account.decision_at = datetime.now(timezone.utc)
    account.decision_notes = notes

    # If revoking access, create a remediation task
    if decision == "revoked" and account.remediation_task_id is None:
        task = Task(
            title=f"Revoke access: {account.email or account.external_user_id}",
            description=f"Access review {review_id} flagged this account for revocation from {_get_review_system(db, review_id)}.",
            assigned_to=None,
            priority="high",
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        db.add(task)
        db.flush()
        account.remediation_task_id = task.id

    # Update review counters
    review = db.get(AccessReview, review_id)
    if review and previous_decision != decision:
        _recalculate_review_counts(db, review)

    db.flush()
    return {
        "id": account.id,
        "review_id": account.review_id,
        "email": account.email,
        "decision": account.decision,
        "decision_by": account.decision_by,
        "remediation_task_id": account.remediation_task_id,
    }


def complete_review(db: Session, review_id: int, completed_by: int) -> dict[str, Any] | None:
    review = db.get(AccessReview, review_id)
    if review is None:
        return None

    _recalculate_review_counts(db, review)

    if review.accounts_pending > 0:
        return {"error": "All accounts must have a decision before completing the review."}

    review.status = "completed"
    review.completed_at = datetime.now(timezone.utc)
    review.updated_at = datetime.now(timezone.utc)
    db.flush()

    # Auto-generate evidence record for CC6.2, CC6.3, CC6.6
    _generate_evidence(db, review, completed_by)

    return _review_dict(review)


def list_accounts(db: Session, review_id: int) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            select(AccessReviewAccount)
            .where(AccessReviewAccount.review_id == review_id)
            .order_by(AccessReviewAccount.risk_flag.desc(), AccessReviewAccount.email)
        )
        .scalars()
        .all()
    )
    return [_account_dict(a) for a in rows]


def _recalculate_review_counts(db: Session, review: AccessReview) -> None:
    accounts = (
        db.execute(
            select(AccessReviewAccount).where(AccessReviewAccount.review_id == review.id)
        )
        .scalars()
        .all()
    )
    review.accounts_approved = sum(1 for a in accounts if a.decision == "approved")
    review.accounts_revoked = sum(1 for a in accounts if a.decision == "revoked")
    review.accounts_pending = sum(1 for a in accounts if a.decision in (None, "pending"))
    review.total_accounts = len(accounts)


def _get_review_system(db: Session, review_id: int) -> str:
    review = db.get(AccessReview, review_id)
    return review.system_name if review else "unknown"


def _generate_evidence(db: Session, review: AccessReview, completed_by: int) -> None:
    """Create a system_generated evidence record and link it to access controls."""
    from app.models.evidence import Evidence
    from app.models.compliance import EvidenceControl

    now = datetime.now(timezone.utc)
    evidence = Evidence(
        title=f"Access Review: {review.title}",
        description=f"Completed access review for {review.system_name}. "
                    f"Accounts approved: {review.accounts_approved}, revoked: {review.accounts_revoked}.",
        source_type="system_generated",
        status="submitted",
        uploaded_by=completed_by,
        valid_from=str(now.date()),
        file_name=f"access_review_{review.id}.json",
        file_size_bytes=0,
        created_at=now,
        updated_at=now,
    )
    db.add(evidence)
    db.flush()

    # Link to CC6.2 (id depends on seed), CC6.3, CC6.6 via EvidenceControl
    from sqlalchemy import text
    control_codes = ["CC6.2", "CC6.3", "CC6.6"]
    is_first = True
    for code in control_codes:
        row = db.execute(
            text("SELECT id FROM controls WHERE control_code = :code LIMIT 1"),
            {"code": code},
        ).first()
        if row:
            db.add(
                EvidenceControl(
                    evidence_id=evidence.id,
                    control_id=row[0],
                    is_primary=is_first,
                    mapped_by=completed_by,
                )
            )
            if is_first:
                evidence.control_id = row[0]
            is_first = False
    db.flush()


def _review_dict(r: AccessReview) -> dict[str, Any]:
    return {
        "id": r.id,
        "title": r.title,
        "system_name": r.system_name,
        "integration_name": r.integration_name,
        "reviewer_user_id": r.reviewer_user_id,
        "status": r.status,
        "due_date": str(r.due_date) if r.due_date else None,
        "completed_at": _fmt(r.completed_at),
        "period_start": str(r.period_start) if r.period_start else None,
        "period_end": str(r.period_end) if r.period_end else None,
        "total_accounts": r.total_accounts,
        "accounts_approved": r.accounts_approved,
        "accounts_revoked": r.accounts_revoked,
        "accounts_pending": r.accounts_pending,
        "created_at": _fmt(r.created_at),
    }


def _account_dict(a: AccessReviewAccount) -> dict[str, Any]:
    return {
        "id": a.id,
        "review_id": a.review_id,
        "external_user_id": a.external_user_id,
        "email": a.email,
        "display_name": a.display_name,
        "role_in_system": a.role_in_system,
        "is_admin": a.is_admin,
        "employment_status": a.employment_status,
        "risk_flag": a.risk_flag,
        "decision": a.decision,
        "decision_by": a.decision_by,
        "decision_notes": a.decision_notes,
        "remediation_task_id": a.remediation_task_id,
    }


def _fmt(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)
