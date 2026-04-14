from __future__ import annotations

import csv
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db import get_connection
from app.schemas import AuditCreate, AuditFindingCreate, AuditFindingUpdate, AuditPeriodCreate


LOCKED_ARTIFACTS_DIR = Path("artifacts") / "locked"
EXPORTS_DIR = Path("artifacts") / "exports"


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
