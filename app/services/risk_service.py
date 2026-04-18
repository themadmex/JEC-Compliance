from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.compliance import Risk, RiskControl, RiskHistory

logger = logging.getLogger(__name__)


def list_risks(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(Risk).order_by(Risk.risk_score.desc().nullslast())).scalars().all()
    return [_risk_dict(r) for r in rows]


def get_risk(db: Session, risk_id: int) -> dict[str, Any] | None:
    r = db.get(Risk, risk_id)
    return _risk_dict(r) if r else None


def create_risk(db: Session, data: dict[str, Any], created_by: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    likelihood = data.get("likelihood")
    impact = data.get("impact")
    score = (likelihood * impact) if (likelihood and impact) else None
    risk = Risk(
        title=data["title"],
        description=data.get("description"),
        category=data.get("category"),
        owner_user_id=data.get("owner_user_id"),
        likelihood=likelihood,
        impact=impact,
        risk_score=score,
        inherent_risk_score=score,
        residual_risk_score=data.get("residual_risk_score"),
        treatment=data.get("treatment"),
        treatment_notes=data.get("treatment_notes"),
        status=data.get("status", "open"),
        review_date=data.get("review_date"),
        created_by=created_by,
        created_at=now,
        updated_at=now,
    )
    db.add(risk)
    db.flush()
    return _risk_dict(risk)


def update_risk(db: Session, risk_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    risk = db.get(Risk, risk_id)
    if risk is None:
        return None

    for field in (
        "title", "description", "category", "owner_user_id",
        "likelihood", "impact", "residual_risk_score",
        "treatment", "treatment_notes", "status", "review_date",
    ):
        if field in data and data[field] is not None:
            setattr(risk, field, data[field])

    # Recompute score if both values present
    if risk.likelihood and risk.impact:
        risk.risk_score = risk.likelihood * risk.impact

    risk.updated_at = datetime.now(timezone.utc)
    db.flush()
    return _risk_dict(risk)


def record_review(
    db: Session, risk_id: int, recorded_by: int, notes: str | None = None
) -> dict[str, Any] | None:
    risk = db.get(Risk, risk_id)
    if risk is None:
        return None

    history = RiskHistory(
        risk_id=risk_id,
        likelihood=risk.likelihood,
        impact=risk.impact,
        risk_score=risk.risk_score,
        recorded_by=recorded_by,
        recorded_at=datetime.now(timezone.utc),
        notes=notes,
    )
    db.add(history)
    risk.updated_at = datetime.now(timezone.utc)
    db.flush()
    return _history_dict(history)


def get_risk_history(db: Session, risk_id: int) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            select(RiskHistory)
            .where(RiskHistory.risk_id == risk_id)
            .order_by(RiskHistory.recorded_at.desc())
        )
        .scalars()
        .all()
    )
    return [_history_dict(h) for h in rows]


def link_control(db: Session, risk_id: int, control_id: int) -> None:
    existing = db.execute(
        select(RiskControl).where(
            RiskControl.risk_id == risk_id, RiskControl.control_id == control_id
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(RiskControl(risk_id=risk_id, control_id=control_id))
        db.flush()


def export_csv(db: Session) -> bytes:
    risks = list_risks(db)
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "id", "title", "category", "likelihood", "impact", "risk_score",
            "inherent_risk_score", "residual_risk_score", "treatment",
            "status", "review_date", "description",
        ],
    )
    writer.writeheader()
    for r in risks:
        writer.writerow({k: r.get(k) for k in writer.fieldnames})
    return buf.getvalue().encode("utf-8")


def export_json(db: Session) -> bytes:
    return json.dumps(list_risks(db), default=str, indent=2).encode("utf-8")


def _risk_dict(r: Risk) -> dict[str, Any]:
    return {
        "id": r.id,
        "title": r.title,
        "description": r.description,
        "category": r.category,
        "owner_user_id": r.owner_user_id,
        "likelihood": r.likelihood,
        "impact": r.impact,
        "risk_score": r.risk_score,
        "inherent_risk_score": r.inherent_risk_score,
        "residual_risk_score": r.residual_risk_score,
        "treatment": r.treatment,
        "treatment_notes": r.treatment_notes,
        "status": r.status,
        "review_date": str(r.review_date) if r.review_date else None,
        "created_by": r.created_by,
        "created_at": _fmt(r.created_at),
        "updated_at": _fmt(r.updated_at),
    }


def _history_dict(h: RiskHistory) -> dict[str, Any]:
    return {
        "id": h.id,
        "risk_id": h.risk_id,
        "likelihood": h.likelihood,
        "impact": h.impact,
        "risk_score": h.risk_score,
        "recorded_by": h.recorded_by,
        "recorded_at": _fmt(h.recorded_at),
        "notes": h.notes,
    }


def _fmt(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)
