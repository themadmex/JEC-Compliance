from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db import get_connection
from app.schemas import EvidenceCreate


EVIDENCE_STALE_DAYS = 90
LOCKED_ARTIFACTS_DIR = Path("artifacts") / "locked"


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


def get_documents_workspace(controls_list: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = list_evidence()
    controls_map = {control["id"]: control for control in controls_list}
    attention_statuses = {"pending", "rejected", "stale"}
    items = [
        {
            **item,
            "control_ref": controls_map.get(item["control_id"], {}).get("control_id"),
            "control_title": controls_map.get(item["control_id"], {}).get("title"),
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
