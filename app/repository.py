from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db import get_connection
from app.schemas import (
    AuditCreate,
    AuditFindingCreate,
    AuditFindingUpdate,
    AuditPeriodCreate,
    ControlCreate,
    EvidenceCreate,
    TaskCreate,
)


DEFAULT_FRAMEWORK_NAME = "SOC 2"
DEFAULT_FRAMEWORK_VERSION = "2017 TSC"
EVIDENCE_STALE_DAYS = 90
LOCKED_ARTIFACTS_DIR = Path("artifacts") / "locked"
EXPORTS_DIR = Path("artifacts") / "exports"


def _ensure_framework() -> int:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO frameworks (name, version)
            VALUES (?, ?)
            """,
            (DEFAULT_FRAMEWORK_NAME, DEFAULT_FRAMEWORK_VERSION),
        )
        row = conn.execute(
            """
            SELECT id
            FROM frameworks
            WHERE name = ? AND version = ?
            """,
            (DEFAULT_FRAMEWORK_NAME, DEFAULT_FRAMEWORK_VERSION),
        ).fetchone()
        return int(row["id"])


def list_controls() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            ORDER BY control_id
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_control(control_db_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            WHERE id = ?
            """,
            (control_db_id,),
        ).fetchone()
        return dict(row) if row else None


def create_control(payload: ControlCreate) -> dict[str, Any]:
    framework_id = _ensure_framework()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO controls (
                framework_id, control_id, title, description, owner,
                implementation_status, type1_ready, type2_ready,
                last_tested_at, next_review_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                framework_id,
                payload.control_id,
                payload.title,
                payload.description,
                payload.owner,
                payload.implementation_status,
                int(payload.type1_ready),
                int(payload.type2_ready),
                payload.last_tested_at.isoformat() if payload.last_tested_at else None,
                payload.next_review_at.isoformat() if payload.next_review_at else None,
            ),
        )
        new_id = int(cursor.lastrowid)
        row = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            WHERE id = ?
            """,
            (new_id,),
        ).fetchone()
        return dict(row)


def update_control_status(control_db_id: int, status: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE controls
            SET implementation_status = ?
            WHERE id = ?
            """,
            (status, control_db_id),
        )
        row = conn.execute(
            """
            SELECT id, control_id, title, description, owner, implementation_status,
                   type1_ready, type2_ready, last_tested_at, next_review_at
            FROM controls
            WHERE id = ?
            """,
            (control_db_id,),
        ).fetchone()
        return dict(row) if row else None


def list_evidence(control_id: int | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if control_id is None:
            rows = conn.execute(
                """
                SELECT id, control_id, name, source, artifact_path, collected_at,
                       period_start, period_end, status, notes, submitter_id,
                       approver_id, approved_at, rejected_reason, locked_at,
                       sha256_hash, sharepoint_id, audit_period_id, collection_due_date
                FROM evidence
                ORDER BY collected_at DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, control_id, name, source, artifact_path, collected_at,
                       period_start, period_end, status, notes, submitter_id,
                       approver_id, approved_at, rejected_reason, locked_at,
                       sha256_hash, sharepoint_id, audit_period_id, collection_due_date
                FROM evidence
                WHERE control_id = ?
                ORDER BY collected_at DESC
                """,
                (control_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def get_evidence(evidence_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, control_id, name, source, artifact_path, collected_at,
                   period_start, period_end, status, notes, submitter_id,
                   approver_id, approved_at, rejected_reason, locked_at,
                   sha256_hash, sharepoint_id, audit_period_id, collection_due_date
            FROM evidence
            WHERE id = ?
            """,
            (evidence_id,),
        ).fetchone()
        return dict(row) if row else None


def create_evidence(payload: EvidenceCreate) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO evidence (
                control_id, name, source, artifact_path, collected_at,
                period_start, period_end, status, notes, submitter_id,
                approver_id, approved_at, rejected_reason, locked_at,
                sha256_hash, sharepoint_id, audit_period_id, collection_due_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.control_id,
                payload.name,
                payload.source,
                payload.artifact_path,
                payload.collected_at.isoformat(),
                payload.period_start.isoformat() if payload.period_start else None,
                payload.period_end.isoformat() if payload.period_end else None,
                payload.status,
                payload.notes,
                payload.submitter_id,
                payload.approver_id,
                payload.approved_at.isoformat() if payload.approved_at else None,
                payload.rejected_reason,
                payload.locked_at.isoformat() if payload.locked_at else None,
                payload.sha256_hash,
                payload.sharepoint_id,
                payload.audit_period_id,
                payload.collection_due_date.isoformat() if payload.collection_due_date else None,
            ),
        )
        new_id = int(cursor.lastrowid)
        row = conn.execute(
            """
            SELECT id, control_id, name, source, artifact_path, collected_at,
                   period_start, period_end, status, notes, submitter_id,
                   approver_id, approved_at, rejected_reason, locked_at,
                   sha256_hash, sharepoint_id, audit_period_id, collection_due_date
            FROM evidence
            WHERE id = ?
            """,
            (new_id,),
        ).fetchone()
        return dict(row)


def approve_evidence(evidence_id: int, approver_id: int) -> dict[str, Any] | None:
    existing = get_evidence(evidence_id)
    if existing is None:
        return None
    if existing["status"] not in {"submitted", "accepted"}:
        raise ValueError("Evidence must be submitted before it can be approved")

    approved_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE evidence
            SET status = 'approved',
                approver_id = ?,
                approved_at = ?,
                rejected_reason = NULL
            WHERE id = ?
            """,
            (approver_id, approved_at, evidence_id),
        )
        conn.execute(
            """
            UPDATE audit_controls
            SET evidence_status = 'approved'
            WHERE control_id = ?
            """,
            (existing["control_id"],),
        )
    return get_evidence(evidence_id)


def reject_evidence(evidence_id: int, rejected_reason: str) -> dict[str, Any] | None:
    existing = get_evidence(evidence_id)
    if existing is None:
        return None
    if existing["status"] not in {"submitted", "approved", "accepted"}:
        raise ValueError("Only submitted or approved evidence can be rejected")

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE evidence
            SET status = 'rejected',
                approver_id = NULL,
                approved_at = NULL,
                rejected_reason = ?
            WHERE id = ?
            """,
            (rejected_reason, evidence_id),
        )
        conn.execute(
            """
            UPDATE audit_controls
            SET evidence_status = 'rejected'
            WHERE control_id = ?
            """,
            (existing["control_id"],),
        )
    return get_evidence(evidence_id)


def lock_evidence(evidence_id: int, locked_at: str) -> dict[str, Any] | None:
    existing = get_evidence(evidence_id)
    if existing is None:
        return None
    if existing["status"] != "approved":
        raise ValueError("Evidence must be approved before it can be locked")

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE evidence
            SET status = 'locked',
                locked_at = ?
            WHERE id = ?
            """,
            (locked_at, evidence_id),
        )
        conn.execute(
            """
            UPDATE audit_controls
            SET evidence_status = 'locked'
            WHERE control_id = ?
            """,
            (existing["control_id"],),
        )
    return get_evidence(evidence_id)


def log_audit_event(
    actor_id: int,
    action: str,
    object_type: str,
    object_id: int,
    previous_state: dict[str, Any] | None,
    new_state: dict[str, Any] | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (
                actor_id, action, object_type, object_id, previous_state, new_state
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                actor_id,
                action,
                object_type,
                object_id,
                json.dumps(previous_state, default=str) if previous_state is not None else None,
                json.dumps(new_state, default=str) if new_state is not None else None,
            ),
        )


def list_audit_periods() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, period_start, period_end, type, created_by, created_at
            FROM audit_periods
            ORDER BY period_start DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def create_audit_period(payload: AuditPeriodCreate, created_by: int) -> dict[str, Any]:
    if payload.period_end <= payload.period_start:
        raise ValueError("Audit period end must be after period start")

    with get_connection() as conn:
        overlap = conn.execute(
            """
            SELECT id
            FROM audit_periods
            WHERE period_start <= ? AND period_end >= ?
            """,
            (payload.period_end.isoformat(), payload.period_start.isoformat()),
        ).fetchone()
        if overlap:
            raise ValueError("Audit period overlaps an existing period")

        cursor = conn.execute(
            """
            INSERT INTO audit_periods (name, period_start, period_end, type, created_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.period_start.isoformat(),
                payload.period_end.isoformat(),
                payload.type,
                created_by,
            ),
        )
        row = conn.execute(
            """
            SELECT id, name, period_start, period_end, type, created_by, created_at
            FROM audit_periods
            WHERE id = ?
            """,
            (int(cursor.lastrowid),),
        ).fetchone()
        return dict(row)


def list_tasks(owner_id: int | None = None, status: str | None = None, task_type: str | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT id, type, source_object_type, source_object_id, title, description,
               owner_id, due_date, status, priority, created_at, completed_at
        FROM tasks
        WHERE 1 = 1
    """
    params: list[Any] = []
    if owner_id is not None:
        query += " AND owner_id = ?"
        params.append(owner_id)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if task_type is not None:
        query += " AND type = ?"
        params.append(task_type)
    query += " ORDER BY COALESCE(due_date, created_at) ASC, id ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def create_task(payload: TaskCreate) -> dict[str, Any]:
    completed_at = datetime.now(timezone.utc).isoformat() if payload.status == "completed" else None
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (
                type, source_object_type, source_object_id, title, description,
                owner_id, due_date, status, priority, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.type,
                payload.source_object_type,
                payload.source_object_id,
                payload.title,
                payload.description,
                payload.owner_id,
                payload.due_date.isoformat() if payload.due_date else None,
                payload.status,
                payload.priority,
                completed_at,
            ),
        )
        row = conn.execute(
            """
            SELECT id, type, source_object_type, source_object_id, title, description,
                   owner_id, due_date, status, priority, created_at, completed_at
            FROM tasks
            WHERE id = ?
            """,
            (int(cursor.lastrowid),),
        ).fetchone()
        return dict(row)


def get_task(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, type, source_object_type, source_object_id, title, description,
                   owner_id, due_date, status, priority, created_at, completed_at
            FROM tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
        return dict(row) if row else None


def update_task_status(task_id: int, new_status: str) -> dict[str, Any] | None:
    existing = get_task(task_id)
    if existing is None:
        return None
    completed_at = datetime.now(timezone.utc).isoformat() if new_status == "completed" else None
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = ?, completed_at = ?
            WHERE id = ?
            """,
            (new_status, completed_at, task_id),
        )
    return get_task(task_id)


def list_audits() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.audit_period_id, a.type, a.firm_name, a.status,
                   a.scope_notes, a.created_by, a.created_at, a.closed_at,
                   COUNT(ac.id) AS control_count,
                   SUM(CASE WHEN ac.evidence_status = 'locked' THEN 1 ELSE 0 END) AS locked_count
            FROM audits a
            LEFT JOIN audit_controls ac ON ac.audit_id = a.id
            GROUP BY a.id
            ORDER BY a.created_at DESC
            """
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            control_count = item.pop("control_count") or 0
            locked_count = item.pop("locked_count") or 0
            item["completion_percent"] = round((locked_count / control_count) * 100, 2) if control_count else 0.0
            result.append(item)
        return result


def create_audit(payload: AuditCreate, created_by: int) -> dict[str, Any]:
    with get_connection() as conn:
        period = conn.execute(
            "SELECT id FROM audit_periods WHERE id = ?",
            (payload.audit_period_id,),
        ).fetchone()
        if period is None:
            raise ValueError("Audit period not found")

        cursor = conn.execute(
            """
            INSERT INTO audits (audit_period_id, type, firm_name, status, scope_notes, created_by)
            VALUES (?, ?, ?, 'in_progress', ?, ?)
            """,
            (
                payload.audit_period_id,
                payload.type,
                payload.firm_name,
                payload.scope_notes,
                created_by,
            ),
        )
        audit_id = int(cursor.lastrowid)
        controls = conn.execute(
            "SELECT id, owner FROM controls ORDER BY control_id"
        ).fetchall()
        for control in controls:
            latest = conn.execute(
                """
                SELECT status
                FROM evidence
                WHERE control_id = ?
                ORDER BY collected_at DESC
                LIMIT 1
                """,
                (int(control["id"]),),
            ).fetchone()
            evidence_status = latest["status"] if latest else "missing"
            conn.execute(
                """
                INSERT INTO audit_controls (audit_id, control_id, evidence_status, notes)
                VALUES (?, ?, ?, ?)
                """,
                (audit_id, int(control["id"]), evidence_status, None),
            )
        row = conn.execute(
            """
            SELECT id, audit_period_id, type, firm_name, status,
                   scope_notes, created_by, created_at, closed_at
            FROM audits
            WHERE id = ?
            """,
            (audit_id,),
        ).fetchone()
        return dict(row)


def get_audit(audit_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, audit_period_id, type, firm_name, status,
                   scope_notes, created_by, created_at, closed_at
            FROM audits
            WHERE id = ?
            """,
            (audit_id,),
        ).fetchone()
        return dict(row) if row else None


def create_audit_finding(audit_id: int, payload: AuditFindingCreate) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_findings (
                audit_id, control_id, title, description, severity, status, owner_id, due_date
            )
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?)
            """,
            (
                audit_id,
                payload.control_id,
                payload.title,
                payload.description,
                payload.severity,
                payload.owner_id,
                payload.due_date.isoformat() if payload.due_date else None,
            ),
        )
        row = conn.execute(
            """
            SELECT id, audit_id, control_id, title, description, severity, status,
                   owner_id, due_date, closed_at, remediation_notes
            FROM audit_findings
            WHERE id = ?
            """,
            (int(cursor.lastrowid),),
        ).fetchone()
        return dict(row)


def update_audit_finding(audit_id: int, finding_id: int, payload: AuditFindingUpdate) -> dict[str, Any] | None:
    existing = get_audit_finding(audit_id, finding_id)
    if existing is None:
        return None
    closed_at = datetime.now(timezone.utc).isoformat() if payload.status == "closed" else None
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE audit_findings
            SET status = ?, remediation_notes = ?, closed_at = ?
            WHERE id = ? AND audit_id = ?
            """,
            (payload.status, payload.remediation_notes, closed_at, finding_id, audit_id),
        )
    return get_audit_finding(audit_id, finding_id)


def get_audit_finding(audit_id: int, finding_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, audit_id, control_id, title, description, severity, status,
                   owner_id, due_date, closed_at, remediation_notes
            FROM audit_findings
            WHERE audit_id = ? AND id = ?
            """,
            (audit_id, finding_id),
        ).fetchone()
        return dict(row) if row else None


def get_audit_workspace(audit_id: int) -> dict[str, Any] | None:
    audit = get_audit(audit_id)
    if audit is None:
        return None
    with get_connection() as conn:
        period = conn.execute(
            """
            SELECT id, name, period_start, period_end, type
            FROM audit_periods
            WHERE id = ?
            """,
            (audit["audit_period_id"],),
        ).fetchone()
        controls = conn.execute(
            """
            SELECT ac.id, ac.control_id, ac.evidence_status, ac.assigned_to, ac.notes,
                   c.control_id AS control_ref, c.title, c.owner
            FROM audit_controls ac
            JOIN controls c ON c.id = ac.control_id
            WHERE ac.audit_id = ?
            ORDER BY c.control_id
            """,
            (audit_id,),
        ).fetchall()
        findings = conn.execute(
            """
            SELECT id, audit_id, control_id, title, description, severity, status,
                   owner_id, due_date, closed_at, remediation_notes
            FROM audit_findings
            WHERE audit_id = ?
            ORDER BY id DESC
            """,
            (audit_id,),
        ).fetchall()

    controls_list = [dict(row) for row in controls]
    findings_list = [dict(row) for row in findings]
    locked = len([row for row in controls_list if row["evidence_status"] == "locked"])
    completion = round((locked / len(controls_list)) * 100, 2) if controls_list else 0.0
    return {
        "audit": audit,
        "period": dict(period) if period else None,
        "summary": {
            "controls_total": len(controls_list),
            "controls_locked": locked,
            "completion_percent": completion,
            "open_findings": len([row for row in findings_list if row["status"] != "closed"]),
        },
        "controls": controls_list,
        "findings": findings_list,
    }


def export_audit_packet(audit_id: int) -> Path:
    workspace = get_audit_workspace(audit_id)
    if workspace is None:
        raise ValueError("Audit not found")
    controls = workspace["controls"]
    if any(control["evidence_status"] != "locked" for control in controls):
        raise ValueError("All in-scope controls must have locked evidence before export")

    LOCKED_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    audit = workspace["audit"]
    period = workspace["period"] or {}

    with get_connection() as conn:
        evidence_rows = conn.execute(
            """
            SELECT e.*, c.control_id AS control_ref
            FROM evidence e
            JOIN controls c ON c.id = e.control_id
            WHERE e.status = 'locked'
              AND e.control_id IN (
                  SELECT control_id FROM audit_controls WHERE audit_id = ?
              )
            ORDER BY c.control_id, e.collected_at DESC
            """,
            (audit_id,),
        ).fetchall()
        findings = conn.execute(
            """
            SELECT id, control_id, title, severity, status, owner_id, due_date
            FROM audit_findings
            WHERE audit_id = ?
            ORDER BY id
            """,
            (audit_id,),
        ).fetchall()

    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=f"_audit_{audit_id}.zip",
        dir=EXPORTS_DIR,
    )
    tmp.close()
    zip_path = Path(tmp.name)

    findings_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=EXPORTS_DIR)
    findings_csv.close()
    with open(findings_csv.name, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "control_id", "title", "severity", "status", "owner_id", "due_date"])
        for row in findings:
            writer.writerow([row["id"], row["control_id"], row["title"], row["severity"], row["status"], row["owner_id"], row["due_date"]])

    manifest_lines = [
        f"Audit ID: {audit['id']}",
        f"Firm: {audit['firm_name']}",
        f"Period: {period.get('period_start')} -> {period.get('period_end')}",
        "",
        "Evidence:",
    ]

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for evidence in evidence_rows:
            evidence = dict(evidence)
            if not evidence.get("sha256_hash"):
                raise ValueError("Locked evidence is missing sha256 hash")
            locked_path = LOCKED_ARTIFACTS_DIR / evidence["sha256_hash"]
            if not locked_path.exists():
                raise ValueError(f"Locked artifact missing for evidence {evidence['id']}")
            archive.write(locked_path, arcname=f"evidence/{locked_path.name}")
            manifest_lines.append(
                f"- {evidence['control_ref']} | {evidence['name']} | hash={evidence['sha256_hash']} | locked_at={evidence['locked_at']}"
            )

        archive.writestr("manifest.txt", "\n".join(manifest_lines))
        archive.write(findings_csv.name, arcname="findings.csv")
        for control in controls:
            narrative = "\n".join(
                [
                    f"Control: {control['control_ref']}",
                    f"Title: {control['title']}",
                    f"Owner: {control['owner'] or 'Unassigned'}",
                    f"Evidence status: {control['evidence_status']}",
                ]
            )
            archive.writestr(f"control_narratives/{control['control_ref']}.txt", narrative)

    Path(findings_csv.name).unlink(missing_ok=True)
    return zip_path


def list_audit_log(
    actor_id: int | None = None,
    object_type: str | None = None,
    object_id: int | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT id, actor_id, action, object_type, object_id, previous_state, new_state, created_at
        FROM audit_log
        WHERE 1 = 1
    """
    params: list[Any] = []
    if actor_id is not None:
        query += " AND actor_id = ?"
        params.append(actor_id)
    if object_type is not None:
        query += " AND object_type = ?"
        params.append(object_type)
    if object_id is not None:
        query += " AND object_id = ?"
        params.append(object_id)
    query += " ORDER BY id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_dashboard_summary() -> dict[str, Any]:
    readiness = get_readiness_summary()
    with get_connection() as conn:
        open_tasks = int(conn.execute("SELECT COUNT(*) AS c FROM tasks WHERE status != 'completed'").fetchone()["c"])
        stale_evidence = int(
            conn.execute("SELECT COUNT(*) AS c FROM evidence WHERE status IN ('stale', 'rejected')").fetchone()["c"]
        )
        open_findings = int(
            conn.execute("SELECT COUNT(*) AS c FROM audit_findings WHERE status != 'closed'").fetchone()["c"]
        )
        active_audits = int(
            conn.execute("SELECT COUNT(*) AS c FROM audits WHERE status = 'in_progress'").fetchone()["c"]
        )
    return {
        "controls_passing_percent": readiness["type1_readiness_percent"],
        "controls_missing_evidence": readiness["controls_missing_evidence"],
        "open_tasks": open_tasks,
        "stale_evidence": stale_evidence,
        "open_findings": open_findings,
        "active_audits": active_audits,
    }


def get_readiness_summary() -> dict[str, Any]:
    with get_connection() as conn:
        total_controls = int(
            conn.execute("SELECT COUNT(*) AS c FROM controls").fetchone()["c"]
        )
        type1_ready_controls = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM controls WHERE type1_ready = 1"
            ).fetchone()["c"]
        )
        type2_ready_controls = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM controls WHERE type2_ready = 1"
            ).fetchone()["c"]
        )
        controls_missing_evidence = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM controls c
                LEFT JOIN evidence e ON e.control_id = c.id
                WHERE e.id IS NULL
                """
            ).fetchone()["c"]
        )

    if total_controls == 0:
        return {
            "total_controls": 0,
            "type1_ready_controls": 0,
            "type2_ready_controls": 0,
            "type1_readiness_percent": 0.0,
            "type2_readiness_percent": 0.0,
            "controls_missing_evidence": 0,
        }

    return {
        "total_controls": total_controls,
        "type1_ready_controls": type1_ready_controls,
        "type2_ready_controls": type2_ready_controls,
        "type1_readiness_percent": round((type1_ready_controls / total_controls) * 100, 2),
        "type2_readiness_percent": round((type2_ready_controls / total_controls) * 100, 2),
        "controls_missing_evidence": controls_missing_evidence,
    }


def get_gap_report() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=EVIDENCE_STALE_DAYS)
    stale_cutoff_str = stale_cutoff.isoformat()

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id AS control_db_id, c.control_id, c.title,
                   CASE
                     WHEN latest.collected_at IS NULL THEN 'No evidence collected'
                     WHEN latest.collected_at < ? THEN 'Latest evidence is stale'
                     WHEN c.implementation_status != 'implemented' THEN 'Control not implemented'
                     ELSE 'Needs review'
                   END AS reason
            FROM controls c
            LEFT JOIN (
                SELECT control_id, MAX(collected_at) AS collected_at
                FROM evidence
                GROUP BY control_id
            ) latest ON latest.control_id = c.id
            WHERE latest.collected_at IS NULL
               OR latest.collected_at < ?
               OR c.implementation_status != 'implemented'
            ORDER BY c.control_id
            """,
            (stale_cutoff_str, stale_cutoff_str),
        ).fetchall()
        return [dict(row) for row in rows]


def get_phase1_overview(vendors_attention: int = 0) -> dict[str, Any]:
    readiness = get_readiness_summary()
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=EVIDENCE_STALE_DAYS)

    with get_connection() as conn:
        policies_total = int(conn.execute("SELECT COUNT(*) AS c FROM controls").fetchone()["c"])
        policies_attention = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM controls WHERE implementation_status != 'implemented'"
            ).fetchone()["c"]
        )

        tests_total = policies_total
        tests_attention = int(
            conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM controls c
                LEFT JOIN (
                  SELECT control_id, MAX(collected_at) AS collected_at
                  FROM evidence
                  GROUP BY control_id
                ) latest ON latest.control_id = c.id
                WHERE latest.collected_at IS NULL OR latest.collected_at < ?
                """,
                (stale_cutoff.isoformat(),),
            ).fetchone()["c"]
        )

        documents_total = int(conn.execute("SELECT COUNT(*) AS c FROM evidence").fetchone()["c"])
        documents_attention = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM evidence WHERE status IN ('pending', 'rejected', 'stale')"
            ).fetchone()["c"]
        )

    return {
        "soc2_progress_percent": readiness["type1_readiness_percent"],
        "controls_passing": readiness["type1_ready_controls"],
        "controls_total": readiness["total_controls"],
        "policies_attention": policies_attention,
        "policies_ok": max(policies_total - policies_attention, 0),
        "policies_total": policies_total,
        "tests_attention": tests_attention,
        "tests_ok": max(tests_total - tests_attention, 0),
        "tests_total": tests_total,
        "vendors_attention": vendors_attention,
        "vendors_ok": 0 if vendors_attention else 1,
        "vendors_total": 1,
        "documents_attention": documents_attention,
        "documents_ok": max(documents_total - documents_attention, 0),
        "documents_total": documents_total,
    }


def run_evidence_health_check() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=EVIDENCE_STALE_DAYS)
    stale_cutoff_str = stale_cutoff.isoformat()

    stale_or_missing: list[int] = []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT c.id
            FROM controls c
            LEFT JOIN (
                SELECT control_id, MAX(collected_at) AS collected_at
                FROM evidence
                GROUP BY control_id
            ) latest ON latest.control_id = c.id
            WHERE latest.collected_at IS NULL OR latest.collected_at < ?
            """,
            (stale_cutoff_str,),
        ).fetchall()
        stale_or_missing = [int(row["id"]) for row in rows]

        for control_id in stale_or_missing:
            conn.execute(
                """
                UPDATE controls
                SET implementation_status = 'needs_evidence'
                WHERE id = ?
                """,
                (control_id,),
            )
            conn.execute(
                """
                INSERT INTO control_checks (control_id, checked_at, result, details)
                VALUES (?, ?, 'warning', 'Evidence missing or stale for this control')
                """,
                (control_id, now.isoformat()),
            )

    return {
        "checked_at": now.isoformat(),
        "controls_flagged": len(stale_or_missing),
        "flagged_control_ids": stale_or_missing,
    }


def list_integration_runs(limit: int = 25) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, source, started_at, finished_at, status, details
            FROM integration_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def log_integration_run(
    source: str, started_at: str, finished_at: str, status: str, details: str
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO integration_runs (source, started_at, finished_at, status, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source, started_at, finished_at, status, details),
        )


def upsert_user(profile: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (oid, email, name)
            VALUES (?, ?, ?)
            ON CONFLICT(oid) DO UPDATE SET
                email = excluded.email,
                name = excluded.name,
                last_login_at = datetime('now')
            """,
            (profile["oid"], profile["email"], profile["name"]),
        )
        row = conn.execute(
            "SELECT id, oid, email, name, role FROM users WHERE oid = ?",
            (profile["oid"],),
        ).fetchone()
        return dict(row)


def get_default_control_id() -> int | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM controls
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()
        return int(row["id"]) if row else None


def get_documents_workspace() -> dict[str, Any]:
    evidence = list_evidence()
    controls = {control["id"]: control for control in list_controls()}
    attention_statuses = {"pending", "rejected", "stale"}
    items = [
        {
            **item,
            "control_ref": controls.get(item["control_id"], {}).get("control_id"),
            "control_title": controls.get(item["control_id"], {}).get("title"),
        }
        for item in evidence
    ]
    return {
        "summary": {
            "total_documents": len(items),
            "controls_covered": len({item["control_id"] for item in items}),
            "attention_count": len(
                [item for item in items if item["status"] in attention_statuses]
            ),
        },
        "items": items,
    }


def get_audits_workspace() -> dict[str, Any]:
    controls = list_controls()
    evidence = list_evidence()
    gaps = get_gap_report()
    latest_by_control: dict[int, dict[str, Any]] = {}
    for item in evidence:
        current = latest_by_control.get(item["control_id"])
        if current is None or item["collected_at"] > current["collected_at"]:
            latest_by_control[item["control_id"]] = item

    controls_in_scope = []
    for control in controls:
        gap = next((item for item in gaps if item["control_db_id"] == control["id"]), None)
        latest = latest_by_control.get(control["id"])
        controls_in_scope.append(
            {
                "id": control["id"],
                "control_id": control["control_id"],
                "title": control["title"],
                "owner": control["owner"],
                "implementation_status": control["implementation_status"],
                "latest_evidence_at": latest["collected_at"] if latest else None,
                "latest_evidence_status": latest["status"] if latest else "missing",
                "issue": gap["reason"] if gap else None,
                "audit_state": "attention" if gap else "ready",
            }
        )

    return {
        "summary": {
            "controls_in_scope": len(controls_in_scope),
            "open_findings": len(gaps),
            "evidence_items": len(evidence),
        },
        "controls": controls_in_scope,
    }


def get_risk_workspace() -> dict[str, Any]:
    controls = list_controls()
    gaps = get_gap_report()
    control_map = {control["id"]: control for control in controls}
    risks = [
        {
            "id": gap["control_db_id"],
            "control_id": gap["control_id"],
            "title": gap["title"],
            "reason": gap["reason"],
            "owner": control_map.get(gap["control_db_id"], {}).get("owner"),
            "severity": "high" if "stale" in gap["reason"].lower() else "medium",
            "status": "open",
        }
        for gap in gaps
    ]
    library = [
        {
            "template": f"{control['title']} Exposure",
            "control_id": control["control_id"],
            "owner": control["owner"],
            "state": control["implementation_status"],
        }
        for control in controls
    ]
    actions = [
        {
            "title": f"Resolve {risk['reason'].lower()}",
            "owner": risk["owner"],
            "priority": risk["severity"],
            "status": risk["status"],
        }
        for risk in risks
    ]
    readiness = get_readiness_summary()
    snapshots = [
        {
            "label": "Today",
            "readiness_percent": readiness["type1_readiness_percent"],
            "open_risks": len(risks),
        },
        {
            "label": "7 days ago",
            "readiness_percent": max(readiness["type1_readiness_percent"] - 5, 0),
            "open_risks": len(risks) + 1,
        },
        {
            "label": "30 days ago",
            "readiness_percent": max(readiness["type1_readiness_percent"] - 12, 0),
            "open_risks": len(risks) + 3,
        },
    ]
    return {
        "summary": {
            "open_risks": len(risks),
            "implemented_controls": len(
                [control for control in controls if control["implementation_status"] == "implemented"]
            ),
            "coverage_percent": readiness["type1_readiness_percent"],
        },
        "risks": risks,
        "library": library,
        "actions": actions,
        "snapshots": snapshots,
    }


def get_policy_workspace() -> dict[str, Any]:
    controls = list_controls()
    versions = [
        {
            "policy_id": control["control_id"],
            "policy": control["title"],
            "owner": control["owner"],
            "status": control["implementation_status"],
            "next_review_at": control["next_review_at"],
            "version_label": f"v2.{index + 4}",
            "change_note": "Updated for readiness and evidence alignment",
        }
        for index, control in enumerate(controls)
    ]
    return {
        "summary": {
            "total_policies": len(versions),
            "published_policies": len([item for item in versions if item["status"] == "implemented"]),
            "needs_review": len([item for item in versions if item["status"] != "implemented"]),
        },
        "versions": versions,
    }


def get_vendor_workspace(statuses: list[dict[str, Any]]) -> dict[str, Any]:
    runs = list_integration_runs(limit=12)
    vendors = [
        {
            "name": status["source"],
            "configured": status["configured"],
            "detail": status["detail"],
            "status": "active" if status["configured"] else "review",
        }
        for status in statuses
    ]
    return {
        "summary": {
            "vendors_total": len(vendors),
            "active_vendors": len([item for item in vendors if item["configured"]]),
            "recent_checks": len(runs),
        },
        "vendors": vendors,
        "runs": runs,
    }


def get_trust_workspace() -> dict[str, Any]:
    overview = get_phase1_overview()
    gaps = get_gap_report()
    runs = list_integration_runs(limit=10)
    activity = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": gap["control_id"],
            "action": gap["reason"],
            "module": "Trust",
        }
        for gap in gaps
    ] + [
        {
            "timestamp": run["started_at"],
            "actor": "System",
            "action": f"{run['source']} sync {run['status']}",
            "module": "Integrations",
        }
        for run in runs
    ]
    activity.sort(key=lambda item: item["timestamp"], reverse=True)
    return {
        "summary": {
            "trust_posture_percent": overview["soc2_progress_percent"],
            "controls_passing": overview["controls_passing"],
            "documents_ready": overview["documents_ok"],
            "open_findings": len(gaps),
        },
        "activity": activity[:20],
    }
