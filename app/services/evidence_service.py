from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db import get_connection, get_table_columns
from app.schemas import EvidenceCreate


EVIDENCE_STALE_DAYS = 30
LOCKED_ARTIFACTS_DIR = Path("artifacts") / "locked"


def list_evidence(control_id: int | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if control_id is None:
            rows = conn.execute(
                """
                SELECT id, control_id, title, description, source_type, status,
                       uploaded_by, reviewed_by, rejection_reason, valid_from,
                       valid_to, sha256_hash, sharepoint_url, sharepoint_item_id,
                       local_path, file_name, file_size_bytes, mime_type,
                       locked_at, locked_by, audit_period_id, collection_due_date,
                       created_at, updated_at
                FROM evidence
                ORDER BY created_at DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, control_id, title, description, source_type, status,
                       uploaded_by, reviewed_by, rejection_reason, valid_from,
                       valid_to, sha256_hash, sharepoint_url, sharepoint_item_id,
                       local_path, file_name, file_size_bytes, mime_type,
                       locked_at, locked_by, audit_period_id, collection_due_date,
                       created_at, updated_at
                FROM evidence
                WHERE control_id = ?
                ORDER BY created_at DESC
                """,
                (control_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def get_evidence(evidence_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, control_id, title, description, source_type, status,
                   uploaded_by, reviewed_by, rejection_reason, valid_from,
                   valid_to, sha256_hash, sharepoint_url, sharepoint_item_id,
                   local_path, file_name, file_size_bytes, mime_type,
                   locked_at, locked_by, audit_period_id, collection_due_date,
                   created_at, updated_at
            FROM evidence
            WHERE id = ?
            """,
            (evidence_id,),
        ).fetchone()
        return dict(row) if row else None


def create_evidence(payload: EvidenceCreate) -> dict[str, Any]:
    with get_connection() as conn:
        table_columns = get_table_columns(conn, "evidence")
        columns: list[str] = [
            "control_id",
            "title",
            "description",
            "source_type",
            "status",
            "uploaded_by",
            "reviewed_by",
            "rejection_reason",
            "valid_from",
            "valid_to",
            "sha256_hash",
            "sharepoint_url",
            "sharepoint_item_id",
            "local_path",
            "file_name",
            "file_size_bytes",
            "mime_type",
            "locked_at",
            "locked_by",
            "audit_period_id",
            "collection_due_date",
            "created_at",
            "updated_at",
        ]
        values: list[Any] = [
            payload.control_id,
            payload.title,
            payload.description,
            payload.source_type,
            payload.status,
            payload.uploaded_by,
            payload.reviewed_by,
            payload.rejection_reason,
            payload.valid_from.isoformat(),
            payload.valid_to.isoformat() if payload.valid_to else None,
            payload.sha256_hash,
            payload.sharepoint_url,
            payload.sharepoint_item_id,
            payload.local_path,
            payload.file_name,
            payload.file_size_bytes,
            payload.mime_type,
            payload.locked_at.isoformat() if payload.locked_at else None,
            payload.locked_by,
            payload.audit_period_id,
            payload.collection_due_date.isoformat() if payload.collection_due_date else None,
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat(),
        ]
        legacy_values = {
            "name": payload.title,
            "source": payload.source_type,
            "artifact_path": payload.local_path or payload.sharepoint_url or "",
            "collected_at": payload.valid_from.isoformat(),
            "period_start": payload.valid_from.isoformat(),
            "period_end": payload.valid_to.isoformat() if payload.valid_to else None,
            "notes": payload.description,
            "submitter_id": payload.uploaded_by,
            "approver_id": payload.reviewed_by,
            "rejected_reason": payload.rejection_reason,
            "sharepoint_id": payload.sharepoint_item_id,
        }
        for column, value in legacy_values.items():
            if column in table_columns:
                columns.append(column)
                values.append(value)
        present_columns = [column for column in columns if column in table_columns]
        present_values = [value for column, value in zip(columns, values) if column in table_columns]
        cursor = conn.execute(
            f"""
            INSERT INTO evidence ({", ".join(present_columns)})
            VALUES ({", ".join(["?"] * len(present_values))})
            RETURNING id
            """,
            tuple(present_values),
        )
        new_id = int(cursor.fetchone()["id"])
    created = get_evidence(new_id)
    if created is None:
        raise RuntimeError("Evidence insert succeeded but row could not be reloaded")
    return created


def approve_evidence(evidence_id: int, reviewer_id: int) -> dict[str, Any] | None:
    existing = get_evidence(evidence_id)
    if existing is None:
        return None
    now_str = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE evidence
            SET status = 'accepted',
                reviewed_by = ?,
                updated_at = ?,
                rejection_reason = NULL
            WHERE id = ?
            """,
            (reviewer_id, now_str, evidence_id),
        )
    return get_evidence(evidence_id)


def reject_evidence(evidence_id: int, reviewer_id: int, rejected_reason: str) -> dict[str, Any] | None:
    existing = get_evidence(evidence_id)
    if existing is None:
        return None
    if existing["status"] not in {"submitted", "accepted"}:
        raise ValueError("Only submitted or accepted evidence can be rejected")

    now_str = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE evidence
            SET status = 'rejected',
                reviewed_by = ?,
                updated_at = ?,
                rejection_reason = ?
            WHERE id = ?
            """,
            (reviewer_id, now_str, rejected_reason, evidence_id),
        )
    return get_evidence(evidence_id)


def lock_evidence(evidence_id: int, locked_by: int, locked_at: str) -> dict[str, Any] | None:
    existing = get_evidence(evidence_id)
    if existing is None:
        return None
    if existing["status"] != "accepted":
        raise ValueError("Evidence must be accepted before it can be locked")

    now_str = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE evidence
            SET status = 'locked',
                locked_at = ?,
                locked_by = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (locked_at, locked_by, now_str, evidence_id),
        )
    return get_evidence(evidence_id)


def run_evidence_health_check() -> dict[str, Any]:
    """Scan evidence for stale/expired states and flag controls with missing evidence."""
    now = datetime.now(timezone.utc)
    stale_limit = now + timedelta(days=EVIDENCE_STALE_DAYS)
    
    with get_connection() as conn:
        # 1. Mark expired evidence (past valid_to)
        expired_count = conn.execute(
            """
            UPDATE evidence
            SET status = 'expired',
                updated_at = ?
            WHERE status NOT IN ('locked', 'expired')
              AND valid_to IS NOT NULL
              AND valid_to < ?
            """,
            (now.isoformat(), now.isoformat()),
        ).rowcount
        
        # 2. Mark stale evidence (within 30 days of valid_to)
        stale_count = conn.execute(
            """
            UPDATE evidence
            SET status = 'stale',
                updated_at = ?
            WHERE status NOT IN ('locked', 'expired', 'stale')
              AND valid_to IS NOT NULL
              AND valid_to < ?
            """,
            (now.isoformat(), stale_limit.isoformat()),
        ).rowcount
        
        # 3. Check for controls missing evidence (legacy check)
        stale_cutoff_str = (now - timedelta(days=EVIDENCE_STALE_DAYS)).isoformat()
        rows = conn.execute(
            """
            SELECT c.id
            FROM controls c
            LEFT JOIN (
                SELECT control_id, MAX(valid_from) AS last_collected
                FROM evidence
                GROUP BY control_id
            ) latest ON latest.control_id = c.id
            WHERE latest.last_collected IS NULL OR latest.last_collected < ?
            """,
            (stale_cutoff_str,),
        ).fetchall()
        stale_control_ids = [int(row["id"]) for row in rows]

        for cid in stale_control_ids:
            conn.execute(
                "UPDATE controls SET implementation_status = 'needs_evidence' WHERE id = ?",
                (cid,),
            )
            conn.execute(
                """
                INSERT INTO control_checks (control_id, checked_at, result, details)
                VALUES (?, ?, 'warning', 'Evidence missing or stale for this control')
                """,
                (cid, now.isoformat()),
            )

    return {
        "ok": True,
        "processed_at": now.isoformat(),
        "evidence_expired": expired_count,
        "evidence_stale": stale_count,
        "controls_needs_evidence_flagged": len(stale_control_ids),
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
