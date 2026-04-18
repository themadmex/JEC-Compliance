from __future__ import annotations

import json
import secrets
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db import get_connection
from app.services.log_service import log_audit_event
from app.schemas import (
    AuditCommentCreate,
    AuditControlUpdate,
    AuditCreate,
    AuditFindingCreate,
    AuditFindingUpdate,
    AuditPeriodCreate,
    AuditRequestCreate,
    AuditRequestEvidenceCreate,
    AuditRequestUpdate,
    AuditUpdate,
    AuditorAssignmentCreate,
)


LOCKED_ARTIFACTS_DIR = Path("artifacts") / "locked"
EXPORTS_DIR = Path("artifacts") / "exports"
AUDIT_STATUSES = ["preparation", "in_progress", "fieldwork", "review", "completed", "cancelled"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def _bool(value: Any) -> bool:
    return bool(int(value)) if isinstance(value, int) else bool(value)


def _audit_row(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["period_id"] = item.get("period_id") or item.get("audit_period_id")
    item["audit_firm"] = item.get("audit_firm") or item.get("firm_name")
    return item


def _period_window(period: dict[str, Any]) -> tuple[str | None, str | None]:
    if period.get("report_type") == "type1":
        pit = period.get("point_in_time_date")
        return pit, pit
    return period.get("observation_start"), period.get("observation_end")


def _get_period_for_audit(conn: Any, audit_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT p.*
        FROM audit_periods p
        JOIN audits a ON a.period_id = p.id OR a.audit_period_id = p.id
        WHERE a.id = ?
        """,
        (audit_id,),
    ).fetchone()
    return dict(row) if row else None


def _audit_select(where: str = "", params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT audits.id, audit_period_id, period_id, type, firm_name, audit_firm, status,
                   scope_notes, early_access_date, fieldwork_start, fieldwork_end,
                   report_date, lead_auditor_email, notes, audits.created_by, audits.created_at,
                   updated_at, closed_at
            FROM audits
            {where}
            ORDER BY created_at DESC
            """,
            params,
        ).fetchall()
    return [_audit_row(row) for row in rows]


def list_audits() -> list[dict[str, Any]]:
    return _audit_select()


def list_audits_for_auditor(user_id: int) -> list[dict[str, Any]]:
    return _audit_select(
        """
        JOIN audit_users au ON au.audit_id = audits.id
        WHERE au.user_id = ?
          AND (au.access_expires_at IS NULL OR au.access_expires_at >= ?)
        """,
        (user_id, _now()),
    )


def get_audit(audit_id: int) -> dict[str, Any] | None:
    rows = _audit_select("WHERE id = ?", (audit_id,))
    return rows[0] if rows else None


def create_audit_period(payload: AuditPeriodCreate, created_by: int) -> dict[str, Any]:
    if payload.report_type == "type1" and not payload.point_in_time_date:
        raise ValueError("Type I audit periods require point_in_time_date")
    if payload.report_type == "type2":
        if not payload.observation_start or not payload.observation_end:
            raise ValueError("Type II audit periods require observation_start and observation_end")
        if payload.observation_end <= payload.observation_start:
            raise ValueError("observation_end must be after observation_start")

    with get_connection() as conn:
        framework = conn.execute("SELECT id FROM frameworks WHERE id = ?", (payload.framework_id,)).fetchone()
        if framework is None:
            raise ValueError("Framework not found")
        cursor = conn.execute(
            """
            INSERT INTO audit_periods (
                framework_id, name, period_start, period_end, type, report_type,
                observation_start, observation_end, point_in_time_date, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                payload.framework_id,
                payload.name,
                _iso(payload.observation_start or payload.point_in_time_date),
                _iso(payload.observation_end or payload.point_in_time_date),
                payload.report_type,
                payload.report_type,
                _iso(payload.observation_start),
                _iso(payload.observation_end),
                _iso(payload.point_in_time_date),
                created_by,
            ),
        )
        new_id = int(cursor.fetchone()["id"])
        row = conn.execute(
            """
            SELECT id, framework_id, name, report_type, point_in_time_date,
                   observation_start, observation_end, created_by, created_at
            FROM audit_periods
            WHERE id = ?
            """,
            (new_id,),
        ).fetchone()
    return dict(row)


def list_audit_periods() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, framework_id, name, COALESCE(report_type, type) AS report_type,
                   point_in_time_date, observation_start, observation_end, created_by, created_at
            FROM audit_periods
            ORDER BY created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def create_audit(payload: AuditCreate, created_by: int) -> dict[str, Any]:
    if payload.fieldwork_end <= payload.fieldwork_start:
        raise ValueError("fieldwork_end must be after fieldwork_start")

    with get_connection() as conn:
        period = conn.execute("SELECT * FROM audit_periods WHERE id = ?", (payload.period_id,)).fetchone()
        if period is None:
            raise ValueError("Audit period not found")
        period_dict = dict(period)
        cursor = conn.execute(
            """
            INSERT INTO audits (
                audit_period_id, period_id, type, firm_name, audit_firm, status,
                scope_notes, early_access_date, fieldwork_start, fieldwork_end, notes,
                created_by, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'preparation', ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                payload.period_id,
                payload.period_id,
                period_dict.get("report_type") or period_dict.get("type"),
                payload.audit_firm,
                payload.audit_firm,
                payload.notes,
                _iso(payload.early_access_date),
                _iso(payload.fieldwork_start),
                _iso(payload.fieldwork_end),
                payload.notes,
                created_by,
                _now(),
            ),
        )
        audit_id = int(cursor.fetchone()["id"])
        controls = conn.execute(
            """
            SELECT id
            FROM controls
            WHERE framework_id = ?
            ORDER BY control_id
            """,
            (period_dict.get("framework_id") or 1,),
        ).fetchall()
        for control in controls:
            latest = conn.execute(
                """
                SELECT status
                FROM evidence
                WHERE control_id = ?
                ORDER BY COALESCE(valid_from, created_at) DESC
                LIMIT 1
                """,
                (int(control["id"]),),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO audit_controls (audit_id, control_id, evidence_status, in_scope)
                VALUES (?, ?, ?, 1)
                """,
                (audit_id, int(control["id"]), latest["status"] if latest else "missing"),
            )
    created = get_audit(audit_id)
    if created is None:
        raise RuntimeError("Audit insert succeeded but row could not be reloaded")
    return created


def update_audit(audit_id: int, payload: AuditUpdate) -> dict[str, Any] | None:
    existing = get_audit(audit_id)
    if existing is None:
        return None
    updates: list[str] = []
    values: list[Any] = []
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        if data["status"] not in AUDIT_STATUSES:
            raise ValueError("Unsupported audit status")
        updates.append("status = ?")
        values.append(data["status"])
        if data["status"] == "completed":
            updates.append("closed_at = ?")
            values.append(_now())
    for field in ("early_access_date", "fieldwork_start", "fieldwork_end", "notes"):
        if field in data:
            updates.append(f"{field} = ?")
            value = data[field]
            values.append(_iso(value) if field != "notes" else value)
    if not updates:
        return existing
    updates.append("updated_at = ?")
    values.append(_now())
    values.append(audit_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE audits SET {', '.join(updates)} WHERE id = ?", tuple(values))
        if data.get("status") == "completed":
            conn.execute(
                "UPDATE audit_users SET access_expires_at = ? WHERE audit_id = ?",
                (_now(), audit_id),
            )
    return get_audit(audit_id)


def update_audit_control(audit_id: int, control_id: int, payload: AuditControlUpdate) -> dict[str, Any] | None:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM audit_controls WHERE audit_id = ? AND control_id = ?",
            (audit_id, control_id),
        ).fetchone()
        if existing is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        updates: list[str] = []
        values: list[Any] = []
        if "in_scope" in data and data["in_scope"] is not None:
            updates.append("in_scope = ?")
            values.append(1 if data["in_scope"] else 0)
        if "auditor_notes" in data:
            updates.append("auditor_notes = ?")
            values.append(data["auditor_notes"])
        if updates:
            values.extend([audit_id, control_id])
            conn.execute(
                f"UPDATE audit_controls SET {', '.join(updates)} WHERE audit_id = ? AND control_id = ?",
                tuple(values),
            )
        row = conn.execute(
            "SELECT * FROM audit_controls WHERE audit_id = ? AND control_id = ?",
            (audit_id, control_id),
        ).fetchone()
    return dict(row)


def assign_auditor(audit_id: int, payload: AuditorAssignmentCreate, assigned_by: int) -> dict[str, Any]:
    with get_connection() as conn:
        audit = conn.execute("SELECT * FROM audits WHERE id = ?", (audit_id,)).fetchone()
        if audit is None:
            raise ValueError("Audit not found")
        user = conn.execute("SELECT id, role FROM users WHERE id = ?", (payload.user_id,)).fetchone()
        if user is None:
            raise ValueError("User not found")
        if user["role"] != "auditor":
            raise TypeError("Assigned user must have role='auditor'")
        expiry = payload.access_expires_at
        if expiry is None:
            fieldwork_end = dict(audit).get("fieldwork_end")
            if not fieldwork_end:
                raise ValueError("Audit fieldwork_end is required to assign an auditor")
            expiry = datetime.fromisoformat(str(fieldwork_end)) + timedelta(days=30)
        token = conn.execute(
            "SELECT scoped_token FROM users WHERE id = ?",
            (payload.user_id,),
        ).fetchone()
        if token is None:
            raise ValueError("User not found")
        scoped_token = token["scoped_token"] or secrets.token_urlsafe(32)
        conn.execute(
            """
            UPDATE users
            SET scoped_token = ?, token_expires_at = ?
            WHERE id = ?
            """,
            (scoped_token, _iso(expiry), payload.user_id),
        )
        conn.execute(
            """
            INSERT INTO audit_users (audit_id, user_id, assigned_by, access_expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(audit_id, user_id) DO UPDATE SET
                assigned_by = excluded.assigned_by,
                access_expires_at = excluded.access_expires_at
            """,
            (audit_id, payload.user_id, assigned_by, _iso(expiry)),
        )
        row = conn.execute(
            """
            SELECT au.*, u.email, u.name, u.role, u.scoped_token, u.token_expires_at
            FROM audit_users au
            JOIN users u ON u.id = au.user_id
            WHERE au.audit_id = ? AND au.user_id = ?
            """,
            (audit_id, payload.user_id),
        ).fetchone()
    return dict(row)


def list_audit_auditors(audit_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT au.id, au.audit_id, au.user_id, au.assigned_by, au.assigned_at,
                   au.access_expires_at, u.email, u.name, u.role, u.scoped_token,
                   u.token_expires_at
            FROM audit_users au
            JOIN users u ON u.id = au.user_id
            WHERE au.audit_id = ?
            ORDER BY au.assigned_at DESC, u.name, u.email
            """,
            (audit_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def remove_auditor(audit_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM audit_users WHERE audit_id = ? AND user_id = ?",
            (audit_id, user_id),
        )
    return cursor.rowcount > 0


def auditor_has_scope(audit_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT access_expires_at
            FROM audit_users
            WHERE audit_id = ? AND user_id = ?
            """,
            (audit_id, user_id),
        ).fetchone()
    if row is None:
        return False
    expiry = row["access_expires_at"]
    return not expiry or datetime.now(timezone.utc) <= datetime.fromisoformat(str(expiry))


def _audit_controls(conn: Any, audit_id: int, in_scope_only: bool = False) -> list[dict[str, Any]]:
    _refresh_audit_control_evidence_statuses(conn, audit_id)
    where = "AND ac.in_scope = 1" if in_scope_only else ""
    rows = conn.execute(
        f"""
        SELECT ac.id, ac.audit_id, ac.control_id, ac.evidence_status, ac.assigned_to,
               ac.notes, ac.in_scope, ac.auditor_notes, c.control_id AS control_ref,
               c.control_code, c.title, c.description, c.owner, c.frequency,
               c.is_automated, c.type1_status, c.type2_status
        FROM audit_controls ac
        JOIN controls c ON c.id = ac.control_id
        WHERE ac.audit_id = ? {where}
        ORDER BY c.control_id
        """,
        (audit_id,),
    ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["in_scope"] = _bool(item["in_scope"])
    return items


def _evidence_status_rank(status: str | None) -> int:
    ranks = {
        "missing": 0,
        "submitted": 1,
        "rejected": 1,
        "stale": 1,
        "expired": 1,
        "accepted": 2,
        "locked": 3,
    }
    return ranks.get(status or "missing", 0)


def _best_evidence_status(rows: list[Any]) -> str:
    best = "missing"
    for row in rows:
        status = row["status"]
        if _evidence_status_rank(status) > _evidence_status_rank(best):
            best = status
    return best


def _refresh_audit_control_evidence_statuses(conn: Any, audit_id: int) -> None:
    controls = conn.execute(
        "SELECT control_id FROM audit_controls WHERE audit_id = ? AND in_scope = 1",
        (audit_id,),
    ).fetchall()
    for control in controls:
        control_id = int(control["control_id"])
        rows = conn.execute(
            """
            SELECT e.status
            FROM evidence e
            WHERE e.control_id = ?
               OR e.id IN (
                   SELECT are.evidence_id
                   FROM audit_request_evidence are
                   JOIN audit_requests ar ON ar.id = are.request_id
                   WHERE ar.audit_id = ? AND ar.control_id = ?
               )
            """,
            (control_id, audit_id, control_id),
        ).fetchall()
        conn.execute(
            """
            UPDATE audit_controls
            SET evidence_status = ?
            WHERE audit_id = ? AND control_id = ?
            """,
            (_best_evidence_status(rows), audit_id, control_id),
        )


def _audit_evidence(conn: Any, audit_id: int, period: dict[str, Any] | None) -> list[dict[str, Any]]:
    start, end = _period_window(period or {})
    rows = conn.execute(
        """
        SELECT DISTINCT e.*, c.control_id AS control_ref,
               COALESCE(e.valid_from, e.created_at) AS evidence_sort_at
        FROM evidence e
        JOIN controls c ON c.id = e.control_id
        JOIN audit_controls ac ON ac.control_id = e.control_id AND ac.audit_id = ? AND ac.in_scope = 1
        LEFT JOIN audit_request_evidence are ON are.evidence_id = e.id
        LEFT JOIN audit_requests ar ON ar.id = are.request_id AND ar.audit_id = ?
        WHERE (? IS NULL OR e.valid_from >= ? OR ar.id IS NOT NULL)
          AND (? IS NULL OR e.valid_from <= ? OR ar.id IS NOT NULL)
        ORDER BY control_ref, evidence_sort_at DESC
        """,
        (audit_id, audit_id, start, start, end, end),
    ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item.pop("evidence_sort_at", None)
    return items


def _audit_findings(conn: Any, audit_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, audit_id, control_id, finding_type, severity, title, description,
               management_response, status, owner_id, due_date, closed_at,
               remediation_notes, created_by, created_at, updated_at
        FROM audit_findings
        WHERE audit_id = ?
        ORDER BY id DESC
        """,
        (audit_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_audit_requests(audit_id: int, include_internal: bool = True) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, audit_id, control_id, title, description, due_date, status,
                   requested_by, created_by, assigned_to, request_type, sample_size,
                   created_at, updated_at
            FROM audit_requests
            WHERE audit_id = ?
            ORDER BY created_at DESC
            """,
            (audit_id,),
        ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["comments"] = _request_comments(conn, item["id"], include_internal)
            item["evidence"] = _request_evidence(conn, item["id"])
    return items


def _request_comments(conn: Any, request_id: int, include_internal: bool) -> list[dict[str, Any]]:
    where = "" if include_internal else "AND is_internal = 0"
    rows = conn.execute(
        f"""
        SELECT id, audit_id, request_id, evidence_id, parent_id, author_id, body,
               is_internal, created_at, updated_at
        FROM audit_comments
        WHERE request_id = ? {where}
        ORDER BY created_at
        """,
        (request_id,),
    ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["is_internal"] = _bool(item["is_internal"])
    return items


def _request_evidence(conn: Any, request_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT e.id, e.control_id, e.title, e.status, e.valid_from, e.valid_to,
               e.sha256_hash, e.file_name, are.attached_by, are.created_at
        FROM audit_request_evidence are
        JOIN evidence e ON e.id = are.evidence_id
        WHERE are.request_id = ?
        ORDER BY are.created_at DESC
        """,
        (request_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_request(request_id: int, include_internal: bool = True) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM audit_requests WHERE id = ?", (request_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["comments"] = _request_comments(conn, request_id, include_internal)
        item["evidence"] = _request_evidence(conn, request_id)
    return item


def create_request(audit_id: int, payload: AuditRequestCreate, user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        if conn.execute("SELECT id FROM audits WHERE id = ?", (audit_id,)).fetchone() is None:
            raise ValueError("Audit not found")
        if payload.control_id is not None:
            scoped = conn.execute(
                "SELECT id FROM audit_controls WHERE audit_id = ? AND control_id = ? AND in_scope = 1",
                (audit_id, payload.control_id),
            ).fetchone()
            if scoped is None:
                raise ValueError("Control is not in scope for this audit")
        cursor = conn.execute(
            """
            INSERT INTO audit_requests (
                audit_id, control_id, title, description, due_date, status,
                requested_by, created_by, request_type, sample_size, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                audit_id,
                payload.control_id,
                payload.title,
                payload.description,
                _iso(payload.due_date),
                user_id,
                user_id,
                payload.request_type,
                payload.sample_size,
                _now(),
            ),
        )
        new_id = int(cursor.fetchone()["id"])
    created = get_request(new_id)
    if created is None:
        raise RuntimeError("Request insert succeeded but row could not be reloaded")
    return created


def update_request(request_id: int, payload: AuditRequestUpdate) -> dict[str, Any] | None:
    existing = get_request(request_id)
    if existing is None:
        return None
    updates: list[str] = []
    values: list[Any] = []
    data = payload.model_dump(exclude_unset=True)
    for field in ("status", "assigned_to"):
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])
    if not updates:
        return existing
    updates.append("updated_at = ?")
    values.append(_now())
    values.append(request_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE audit_requests SET {', '.join(updates)} WHERE id = ?", tuple(values))
    return get_request(request_id)


def scan_overdue_audit_requests() -> int:
    now = _now()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM audit_requests
            WHERE due_date IS NOT NULL
              AND due_date < ?
              AND status NOT IN ('fulfilled', 'closed', 'cancelled', 'overdue')
            """,
            (now,),
        ).fetchall()
        requests = [dict(row) for row in rows]
        if not requests:
            return 0
        request_ids = [request["id"] for request in requests]
        placeholders = ", ".join("?" for _ in request_ids)
        conn.execute(
            f"""
            UPDATE audit_requests
            SET status = 'overdue',
                updated_at = ?
            WHERE id IN ({placeholders})
            """,
            (now, *request_ids),
        )

    for request in requests:
        updated = dict(request)
        updated["status"] = "overdue"
        updated["updated_at"] = now
        log_audit_event(
            actor_id=None,
            action="request.overdue",
            object_type="audit_request",
            object_id=int(request["id"]),
            previous_state=request,
            new_state=updated,
        )
    return len(requests)


def attach_request_evidence(request_id: int, payload: AuditRequestEvidenceCreate, user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        req = conn.execute("SELECT audit_id, control_id FROM audit_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            raise ValueError("Request not found")
        ev = conn.execute("SELECT id, control_id, status FROM evidence WHERE id = ?", (payload.evidence_id,)).fetchone()
        if ev is None:
            raise ValueError("Evidence not found")
        request_control_id = req["control_id"]
        if request_control_id is not None and int(ev["control_id"]) != int(request_control_id):
            raise ValueError("Evidence control does not match request control")
        scoped = conn.execute(
            """
            SELECT id
            FROM audit_controls
            WHERE audit_id = ? AND control_id = ? AND in_scope = 1
            """,
            (req["audit_id"], ev["control_id"]),
        ).fetchone()
        if scoped is None:
            raise ValueError("Evidence control is not in scope for this audit")
        conn.execute(
            """
            INSERT INTO audit_request_evidence (request_id, evidence_id, attached_by, attached_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(request_id, evidence_id) DO UPDATE SET
                attached_by = excluded.attached_by,
                attached_at = excluded.attached_at
            """,
            (request_id, payload.evidence_id, user_id, _now()),
        )
        _refresh_audit_control_evidence_statuses(conn, int(req["audit_id"]))
    request = get_request(request_id)
    if request is None:
        raise RuntimeError("Request disappeared after evidence attach")
    return request


def add_request_comment(request_id: int, payload: AuditCommentCreate, user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        req = conn.execute("SELECT audit_id FROM audit_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            raise ValueError("Request not found")
        cursor = conn.execute(
            """
            INSERT INTO audit_comments (
                audit_id, request_id, parent_id, author_id, body, is_internal
            )
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (req["audit_id"], request_id, payload.parent_id, user_id, payload.body, 1 if payload.is_internal else 0),
        )
        row = conn.execute("SELECT * FROM audit_comments WHERE id = ?", (cursor.fetchone()["id"],)).fetchone()
    item = dict(row)
    item["is_internal"] = _bool(item["is_internal"])
    return item


def get_auditor_portal(audit_id: int, include_internal: bool = False) -> dict[str, Any] | None:
    audit = get_audit(audit_id)
    if audit is None:
        return None
    with get_connection() as conn:
        period = _get_period_for_audit(conn, audit_id)
        controls = _audit_controls(conn, audit_id, in_scope_only=True)
        evidence = _audit_evidence(conn, audit_id, period)
        findings = _audit_findings(conn, audit_id)
    return {
        "audit": audit,
        "period": period,
        "controls": controls,
        "evidence": evidence,
        "requests": list_audit_requests(audit_id, include_internal=include_internal),
        "findings": findings,
    }


def get_audit_workspace(audit_id: int) -> dict[str, Any] | None:
    portal = get_auditor_portal(audit_id, include_internal=True)
    if portal is None:
        return None
    controls = portal["controls"]
    findings = portal["findings"]
    locked = len([row for row in controls if row["evidence_status"] == "locked"])
    return {
        **portal,
        "auditors": list_audit_auditors(audit_id),
        "summary": {
            "controls_total": len(controls),
            "controls_locked": locked,
            "completion_percent": round((locked / len(controls)) * 100, 2) if controls else 0.0,
            "open_findings": len([row for row in findings if row["status"] != "closed"]),
        },
    }


def create_audit_finding(audit_id: int, payload: AuditFindingCreate, created_by: int | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        if conn.execute("SELECT id FROM audits WHERE id = ?", (audit_id,)).fetchone() is None:
            raise ValueError("Audit not found")
        cursor = conn.execute(
            """
            INSERT INTO audit_findings (
                audit_id, control_id, finding_type, title, description, severity,
                status, owner_id, due_date, created_by, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
            RETURNING id
            """,
            (
                audit_id,
                payload.control_id,
                payload.finding_type,
                payload.title,
                payload.description,
                payload.severity,
                payload.owner_id,
                _iso(payload.due_date),
                created_by,
                _now(),
            ),
        )
        row = conn.execute("SELECT * FROM audit_findings WHERE id = ?", (cursor.fetchone()["id"],)).fetchone()
    return dict(row)


def get_audit_finding(audit_id: int, finding_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM audit_findings WHERE audit_id = ? AND id = ?",
            (audit_id, finding_id),
        ).fetchone()
    return dict(row) if row else None


def update_audit_finding(audit_id: int, finding_id: int, payload: AuditFindingUpdate) -> dict[str, Any] | None:
    existing = get_audit_finding(audit_id, finding_id)
    if existing is None:
        return None
    closed_at = _now() if payload.status == "closed" else None
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE audit_findings
            SET status = ?, remediation_notes = ?, closed_at = ?, updated_at = ?
            WHERE id = ? AND audit_id = ?
            """,
            (payload.status, payload.remediation_notes, closed_at, _now(), finding_id, audit_id),
        )
    return get_audit_finding(audit_id, finding_id)


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value)
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _frequency_days(frequency: str | None) -> int:
    return {
        "daily": 1,
        "weekly": 7,
        "monthly": 30,
        "quarterly": 90,
        "annual": 365,
        "continuous": 1,
        "on_change": 30,
        "manual": 365,
    }.get(frequency or "manual", 365)


def _latest_check(conn: Any, control_id: int, at_or_before: datetime) -> dict[str, Any] | None:
    rows = conn.execute(
        """
        SELECT id, control_id, COALESCE(status, result) AS status,
               COALESCE(result_summary, details) AS result_summary,
               COALESCE(run_at, checked_at) AS run_at
        FROM control_checks
        WHERE control_id = ?
          AND COALESCE(run_at, checked_at) <= ?
        ORDER BY COALESCE(run_at, checked_at) DESC, id DESC
        LIMIT 1
        """,
        (control_id, at_or_before.isoformat()),
    ).fetchall()
    return dict(rows[0]) if rows else None


def _checks_in_window(conn: Any, control_id: int, start: datetime, end: datetime) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, control_id, COALESCE(status, result) AS status,
               COALESCE(result_summary, details) AS result_summary,
               COALESCE(run_at, checked_at) AS run_at
        FROM control_checks
        WHERE control_id = ?
          AND COALESCE(run_at, checked_at) BETWEEN ? AND ?
        ORDER BY COALESCE(run_at, checked_at), id
        """,
        (control_id, start.isoformat(), end.isoformat()),
    ).fetchall()
    return [dict(row) for row in rows]


def _evidence_rows_for_control(conn: Any, control_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT DISTINCT e.id, e.control_id, e.title, e.status, e.valid_from, e.valid_to,
               e.sha256_hash, e.file_name
        FROM evidence e
        LEFT JOIN evidence_controls ec ON ec.evidence_id = e.id
        WHERE e.control_id = ? OR ec.control_id = ?
        """,
        (control_id, control_id),
    ).fetchall()
    return [dict(row) for row in rows]


def _evidence_covers(evidence: dict[str, Any], start: datetime, end: datetime) -> bool:
    if evidence["status"] not in {"accepted", "locked"}:
        return False
    valid_from = _parse_dt(evidence.get("valid_from"))
    valid_to = _parse_dt(evidence.get("valid_to"))
    if valid_from and valid_from > end:
        return False
    return not valid_to or valid_to >= start


def _month_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    months: list[tuple[datetime, datetime]] = []
    cursor = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while cursor <= end:
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1)
        month_start = max(cursor, start)
        month_end = min(next_month - timedelta(microseconds=1), end)
        months.append((month_start, month_end))
        cursor = next_month
    return months


def _persist_readiness_snapshot(
    conn: Any,
    period_id: int,
    report_type: str,
    result: dict[str, Any],
    gaps: list[dict[str, Any]],
) -> None:
    cursor = conn.execute(
        """
        INSERT INTO readiness_snapshots (
            audit_period_id, report_type, overall_score, controls_ready,
            controls_partial, controls_not_ready, controls_not_applicable, summary_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (
            period_id,
            report_type,
            result["overall_score"],
            result["controls_ready"],
            result["controls_partial"],
            result["controls_not_ready"],
            result["controls_not_applicable"],
            json.dumps(result, default=str),
        ),
    )
    snapshot_id = int(cursor.fetchone()["id"])
    for gap in gaps:
        conn.execute(
            """
            INSERT INTO readiness_gaps (
                snapshot_id, control_id, gap_type, gap_start, gap_end, severity, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                gap["control_id"],
                gap["gap_type"],
                gap.get("gap_start"),
                gap.get("gap_end"),
                gap["severity"],
                gap["detail"],
            ),
        )


def _calculate_type1_readiness(
    conn: Any,
    audit_id: int,
    period: dict[str, Any],
    controls: list[dict[str, Any]],
) -> dict[str, Any]:
    pit = _parse_dt(period.get("point_in_time_date") or period.get("observation_end"))
    if pit is None:
        raise ValueError("Type I readiness requires point_in_time_date")
    output_controls: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for control in controls:
        control_id = int(control["control_id"])
        if control.get("type1_status") == "not_applicable":
            status = "Not Applicable"
            reason = "Control is marked not applicable for Type I."
        else:
            evidence = [row for row in _evidence_rows_for_control(conn, control_id) if _evidence_covers(row, pit, pit)]
            latest_check = _latest_check(conn, control_id, pit)
            is_manual = not _bool(control.get("is_automated"))
            check_status = "pass" if is_manual else (latest_check or {}).get("status")
            if check_status == "pass" and evidence:
                status = "Ready"
                reason = "Passing check and valid evidence are present."
            elif evidence and check_status in {"warning", "skipped"}:
                status = "Partial"
                reason = "Evidence is present, but the latest check is not fully passing."
            else:
                status = "Not Ready"
                reason = "A passing check and valid evidence are both required at the point in time."
            if not evidence:
                gaps.append({
                    "control_id": control_id,
                    "gap_type": "missing_evidence",
                    "gap_start": pit.date().isoformat(),
                    "gap_end": pit.date().isoformat(),
                    "severity": "red",
                    "detail": f"{control['control_code']} has no accepted or locked evidence covering the point in time.",
                })
            if not is_manual and check_status != "pass":
                gaps.append({
                    "control_id": control_id,
                    "gap_type": "missing_or_failing_check",
                    "gap_start": pit.date().isoformat(),
                    "gap_end": pit.date().isoformat(),
                    "severity": "red",
                    "detail": f"{control['control_code']} has no passing automated check on or before the point in time.",
                })
        output = dict(control)
        output["readiness_status"] = status
        output["reason"] = reason
        output_controls.append(output)

    ready = sum(1 for control in output_controls if control["readiness_status"] == "Ready")
    partial = sum(1 for control in output_controls if control["readiness_status"] == "Partial")
    not_applicable = sum(1 for control in output_controls if control["readiness_status"] == "Not Applicable")
    not_ready = len(output_controls) - ready - partial - not_applicable
    denominator = len(output_controls) - not_applicable
    score = round((ready / denominator) * 100, 2) if denominator else 100.0
    result = {
        "audit_id": audit_id,
        "report_type": "type1",
        "calculated_at": _now(),
        "point_in_time_date": pit.isoformat(),
        "overall_score": score,
        "controls_ready": ready,
        "controls_partial": partial,
        "controls_not_ready": not_ready,
        "controls_not_applicable": not_applicable,
        "controls": output_controls,
        "gaps": gaps,
    }
    _persist_readiness_snapshot(conn, int(period["id"]), "type1", result, gaps)
    return result


def _calculate_type2_readiness(
    conn: Any,
    audit_id: int,
    period: dict[str, Any],
    controls: list[dict[str, Any]],
) -> dict[str, Any]:
    start = _parse_dt(period.get("observation_start"))
    end = _parse_dt(period.get("observation_end"))
    if start is None or end is None:
        raise ValueError("Type II readiness requires observation_start and observation_end")
    output_controls: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for control in controls:
        control_id = int(control["control_id"])
        control_gaps: list[dict[str, Any]] = []
        timeline: list[dict[str, Any]] = []
        evidence_rows = _evidence_rows_for_control(conn, control_id)
        checks = _checks_in_window(conn, control_id, start, end)
        is_manual = not _bool(control.get("is_automated"))

        if not is_manual and not checks:
            control_gaps.append({
                "control_id": control_id,
                "gap_type": "missing_checks",
                "gap_start": start.date().isoformat(),
                "gap_end": end.date().isoformat(),
                "severity": "red",
                "detail": f"{control['control_code']} has no automated checks in the observation window.",
            })
        if checks:
            failure_count = sum(1 for check in checks if check["status"] in {"fail", "error"})
            if failure_count / len(checks) > 0.10:
                control_gaps.append({
                    "control_id": control_id,
                    "gap_type": "failure_rate",
                    "gap_start": start.date().isoformat(),
                    "gap_end": end.date().isoformat(),
                    "severity": "red",
                    "detail": f"{control['control_code']} failure rate exceeds 10% in the observation window.",
                })
            expected_days = _frequency_days(control.get("frequency"))
            parsed_checks = [_parse_dt(check["run_at"]) for check in checks]
            parsed_checks = [check for check in parsed_checks if check is not None]
            previous = start
            for check_time in parsed_checks:
                if (check_time - previous).days > expected_days * 2:
                    control_gaps.append({
                        "control_id": control_id,
                        "gap_type": "check_gap",
                        "gap_start": previous.date().isoformat(),
                        "gap_end": check_time.date().isoformat(),
                        "severity": "red",
                        "detail": f"{control['control_code']} check gap exceeded expected cadence.",
                    })
                previous = check_time

        for month_start, month_end in _month_windows(start, end):
            if any(_evidence_covers(row, month_start, month_end) for row in evidence_rows):
                timeline.append({
                    "start_date": month_start.date().isoformat(),
                    "end_date": month_end.date().isoformat(),
                    "color": "green",
                    "reason": "Evidence covers this month.",
                })
                continue
            gap = {
                "control_id": control_id,
                "gap_type": "missing_monthly_evidence",
                "gap_start": month_start.date().isoformat(),
                "gap_end": month_end.date().isoformat(),
                "severity": "red",
                "detail": f"{control['control_code']} has no accepted or locked evidence for this month.",
            }
            control_gaps.append(gap)
            timeline.append({
                "start_date": month_start.date().isoformat(),
                "end_date": month_end.date().isoformat(),
                "color": "red",
                "reason": gap["detail"],
            })

        gaps.extend(control_gaps)
        status = "Operationally Effective" if not control_gaps else "Not Effective"
        output = dict(control)
        output["effectiveness_status"] = status
        output["gap_timeline"] = timeline
        output["reason"] = "No red gap periods found." if status == "Operationally Effective" else "One or more red gap periods found."
        output_controls.append(output)

    effective = sum(1 for control in output_controls if control["effectiveness_status"] == "Operationally Effective")
    not_effective = len(output_controls) - effective
    score = round((effective / len(output_controls)) * 100, 2) if output_controls else 0.0
    result = {
        "audit_id": audit_id,
        "report_type": "type2",
        "calculated_at": _now(),
        "observation_start": start.isoformat(),
        "observation_end": end.isoformat(),
        "overall_score": score,
        "controls_ready": effective,
        "controls_partial": 0,
        "controls_not_ready": not_effective,
        "controls_not_applicable": 0,
        "controls": output_controls,
        "gaps": gaps,
    }
    _persist_readiness_snapshot(conn, int(period["id"]), "type2", result, gaps)
    return result


def calculate_readiness(audit_id: int, report_type: str) -> dict[str, Any]:
    with get_connection() as conn:
        period = _get_period_for_audit(conn, audit_id)
        if period is None:
            raise ValueError("Audit period not found")
        controls = _audit_controls(conn, audit_id, in_scope_only=True)
        if report_type == "type1":
            return _calculate_type1_readiness(conn, audit_id, period, controls)
        if report_type == "type2":
            return _calculate_type2_readiness(conn, audit_id, period, controls)
    raise ValueError("Unsupported readiness report type")


def export_audit_packet(audit_id: int) -> Path:
    workspace = get_audit_workspace(audit_id)
    if workspace is None:
        raise ValueError("Audit not found")
    incomplete = [
        control
        for control in workspace["controls"]
        if control["in_scope"] and control["evidence_status"] != "locked"
    ]
    if incomplete:
        refs = ", ".join(str(control.get("control_ref") or control["control_id"]) for control in incomplete)
        raise ValueError(f"Audit packet is incomplete; controls require locked evidence: {refs}")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_path = EXPORTS_DIR / f"export_{audit_id}_{timestamp}.zip"

    locked_files: list[dict[str, Any]] = []
    manifest = {
        "audit": workspace["audit"],
        "period": workspace["period"],
        "controls": workspace["controls"],
        "evidence": [],
        "generated_at": _now(),
    }

    with get_connection() as conn:
        evidence = _audit_evidence(conn, audit_id, workspace["period"])
        audit_log = conn.execute(
            """
            SELECT id, actor_id, action, object_type, object_id, previous_state, new_state, created_at
            FROM audit_log
            WHERE object_type IN ('audit', 'audit_period', 'audit_finding', 'audit_request', 'evidence')
            ORDER BY created_at
            """
        ).fetchall()

    for row in evidence:
        entry = {
            "id": row["id"],
            "control_id": row["control_id"],
            "control_ref": row.get("control_ref"),
            "title": row.get("title"),
            "status": row.get("status"),
            "sha256_hash": row.get("sha256_hash"),
            "file_name": row.get("file_name"),
            "valid_from": row.get("valid_from"),
            "valid_to": row.get("valid_to"),
        }
        if row.get("status") == "accepted":
            entry["note"] = "Accepted but not locked - file excluded from package"
        if row.get("status") == "locked" and row.get("sha256_hash"):
            locked_path = LOCKED_ARTIFACTS_DIR / row["sha256_hash"]
            if locked_path.exists():
                locked_files.append({"row": row, "path": locked_path})
            else:
                raise ValueError(f"Locked artifact missing for evidence {row['id']}")
        manifest["evidence"].append(entry)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        for control in workspace["controls"]:
            code = control.get("control_code") or control.get("control_ref") or str(control["control_id"])
            archive.writestr(f"controls/{code}.json", json.dumps(control, indent=2, default=str))
        for item in locked_files:
            row = item["row"]
            filename = row.get("file_name") or item["path"].name
            archive.write(item["path"], arcname=f"evidence/{row['id']}/{filename}")
            archive.writestr(
                f"evidence/{row['id']}/metadata.json",
                json.dumps(row, indent=2, default=str),
            )
        archive.writestr("findings/findings.json", json.dumps(workspace["findings"], indent=2, default=str))
        for req in workspace["requests"]:
            archive.writestr(f"requests/{req['id']}.json", json.dumps(req, indent=2, default=str))
        archive.writestr("readiness/type1_snapshot.json", json.dumps(calculate_readiness(audit_id, "type1"), indent=2, default=str))
        archive.writestr("readiness/type2_snapshot.json", json.dumps(calculate_readiness(audit_id, "type2"), indent=2, default=str))
        archive.writestr("audit_log.json", json.dumps([dict(row) for row in audit_log], indent=2, default=str))

    return zip_path
