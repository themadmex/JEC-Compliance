from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.compliance import Personnel, PersonnelComplianceRecord, PersonnelRequirement

logger = logging.getLogger(__name__)


def list_personnel(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(Personnel).order_by(Personnel.display_name)).scalars().all()
    return [_personnel_dict(p, db) for p in rows]


def get_person(db: Session, person_id: int) -> dict[str, Any] | None:
    p = db.get(Personnel, person_id)
    return _personnel_dict(p, db) if p else None


def create_person(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    person = Personnel(
        user_id=data.get("user_id"),
        email=data["email"],
        display_name=data.get("display_name"),
        department=data.get("department"),
        title=data.get("title"),
        employment_status=data.get("employment_status", "active"),
        start_date=data.get("start_date"),
        entra_oid=data.get("entra_oid"),
        created_at=now,
        updated_at=now,
    )
    db.add(person)
    db.flush()
    _provision_requirements(db, person)
    return _personnel_dict(person, db)


def update_person(db: Session, person_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    person = db.get(Personnel, person_id)
    if person is None:
        return None
    for field in ("display_name", "department", "title", "employment_status", "termination_date"):
        if field in data and data[field] is not None:
            setattr(person, field, data[field])
    person.updated_at = datetime.now(timezone.utc)
    db.flush()
    return _personnel_dict(person, db)


def list_requirements(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            select(PersonnelRequirement).where(PersonnelRequirement.is_active == True)
        )
        .scalars()
        .all()
    )
    return [_req_dict(r) for r in rows]


def create_requirement(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    req = PersonnelRequirement(
        title=data["title"],
        requirement_type=data.get("requirement_type", "training"),
        applies_to=data.get("applies_to", "all"),
        due_within_days_of_hire=data.get("due_within_days_of_hire"),
        recurrence_days=data.get("recurrence_days"),
        is_active=True,
        control_id=data.get("control_id"),
    )
    db.add(req)
    db.flush()
    return _req_dict(req)


def mark_completed(
    db: Session,
    person_id: int,
    requirement_id: int,
    evidence_url: str | None,
    notes: str | None,
    completed_by: int,
) -> dict[str, Any] | None:
    record = db.execute(
        select(PersonnelComplianceRecord).where(
            PersonnelComplianceRecord.personnel_id == person_id,
            PersonnelComplianceRecord.requirement_id == requirement_id,
        )
    ).scalar_one_or_none()

    if record is None:
        return None

    now = datetime.now(timezone.utc)
    record.status = "completed"
    record.completed_at = now
    record.evidence_url = evidence_url or record.evidence_url
    record.notes = notes or record.notes
    record.updated_at = now
    db.flush()

    _check_auto_evidence(db, requirement_id, completed_by)

    return _record_dict(record)


def scan_overdue(db: Session) -> int:
    """Mark records past due_date as overdue. Returns count updated."""
    today = str(date.today())
    result = db.execute(
        text(
            """
            UPDATE personnel_compliance_records
            SET status = 'overdue', updated_at = :now
            WHERE status = 'pending'
              AND due_date IS NOT NULL
              AND due_date < :today
            """
        ),
        {"today": today, "now": datetime.now(timezone.utc).isoformat()},
    )
    db.flush()
    return result.rowcount


def _provision_requirements(db: Session, person: Personnel) -> None:
    """Create compliance records for all active requirements that apply to this person."""
    requirements = (
        db.execute(
            select(PersonnelRequirement).where(PersonnelRequirement.is_active == True)
        )
        .scalars()
        .all()
    )
    for req in requirements:
        if req.applies_to not in ("all", person.department):
            continue
        due_date = None
        if req.due_within_days_of_hire and person.start_date:
            try:
                start = date.fromisoformat(str(person.start_date)[:10])
                from datetime import timedelta
                due_date = str(start + timedelta(days=req.due_within_days_of_hire))
            except Exception:
                pass
        existing = db.execute(
            select(PersonnelComplianceRecord).where(
                PersonnelComplianceRecord.personnel_id == person.id,
                PersonnelComplianceRecord.requirement_id == req.id,
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                PersonnelComplianceRecord(
                    personnel_id=person.id,
                    requirement_id=req.id,
                    status="pending",
                    due_date=due_date,
                )
            )
    db.flush()


def _check_auto_evidence(db: Session, requirement_id: int, completed_by: int) -> None:
    """If all active personnel have completed this requirement, auto-generate evidence."""
    req = db.get(PersonnelRequirement, requirement_id)
    if req is None or req.control_id is None:
        return

    total_active = db.execute(
        text("SELECT COUNT(*) FROM personnel WHERE employment_status = 'active'")
    ).scalar() or 0

    completed = db.execute(
        select(PersonnelComplianceRecord).where(
            PersonnelComplianceRecord.requirement_id == requirement_id,
            PersonnelComplianceRecord.status == "completed",
        )
    ).scalars().all()

    if len(completed) >= total_active > 0:
        from app.models.evidence import Evidence
        from app.models.compliance import EvidenceControl

        now = datetime.now(timezone.utc)
        evidence = Evidence(
            control_id=req.control_id,
            title=f"Personnel compliance: {req.title}",
            description=f"All active personnel completed requirement: {req.title}.",
            source_type="system_generated",
            status="submitted",
            uploaded_by=completed_by,
            valid_from=str(now.date()),
            file_name=f"personnel_compliance_{requirement_id}.json",
            file_size_bytes=0,
            created_at=now,
            updated_at=now,
        )
        db.add(evidence)
        db.flush()
        db.add(
            EvidenceControl(
                evidence_id=evidence.id,
                control_id=req.control_id,
                is_primary=True,
                mapped_by=completed_by,
            )
        )
        db.flush()


def _personnel_dict(p: Personnel, db: Session) -> dict[str, Any]:
    records = (
        db.execute(
            select(PersonnelComplianceRecord).where(PersonnelComplianceRecord.personnel_id == p.id)
        )
        .scalars()
        .all()
    )
    overdue_count = sum(1 for r in records if r.status == "overdue")
    pending_count = sum(1 for r in records if r.status == "pending")
    return {
        "id": p.id,
        "user_id": p.user_id,
        "email": p.email,
        "display_name": p.display_name,
        "department": p.department,
        "title": p.title,
        "employment_status": p.employment_status,
        "start_date": str(p.start_date) if p.start_date else None,
        "termination_date": str(p.termination_date) if p.termination_date else None,
        "compliance_summary": {
            "total": len(records),
            "overdue": overdue_count,
            "pending": pending_count,
            "completed": sum(1 for r in records if r.status == "completed"),
        },
        "created_at": _fmt(p.created_at),
    }


def _req_dict(r: PersonnelRequirement) -> dict[str, Any]:
    return {
        "id": r.id,
        "title": r.title,
        "requirement_type": r.requirement_type,
        "applies_to": r.applies_to,
        "due_within_days_of_hire": r.due_within_days_of_hire,
        "recurrence_days": r.recurrence_days,
        "is_active": r.is_active,
        "control_id": r.control_id,
    }


def _record_dict(r: PersonnelComplianceRecord) -> dict[str, Any]:
    return {
        "id": r.id,
        "personnel_id": r.personnel_id,
        "requirement_id": r.requirement_id,
        "status": r.status,
        "completed_at": _fmt(r.completed_at),
        "due_date": str(r.due_date) if r.due_date else None,
        "evidence_url": r.evidence_url,
        "notes": r.notes,
    }


def _fmt(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)
