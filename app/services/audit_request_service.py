from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional


from app.db import get_connection
from app.services.log_service import log_audit_event

logger = logging.getLogger(__name__)

def list_audit_requests(audit_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ar.*, u.name as requester_name, assigned.name as assignee_name
            FROM audit_requests ar
            JOIN users u ON ar.requested_by = u.id
            LEFT JOIN users assigned ON ar.assigned_to = assigned.id
            WHERE ar.audit_id = ?
            ORDER BY ar.created_at DESC
            """,
            (audit_id,),
        ).fetchall()
        return [dict(row) for row in rows]

def create_audit_request(
    audit_id: int,
    requester_id: int,
    title: str,
    description: Optional[str] = None,
    control_id: Optional[int] = None,
    due_date: Optional[str] = None
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO audit_requests (audit_id, requested_by, title, description, control_id, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (audit_id, requester_id, title, description, control_id, due_date),
        )
        request_id = cur.fetchone()["id"]
        
        log_audit_event(
            actor_id=requester_id,
            action="create_audit_request",
            object_type="audit_request",
            object_id=request_id,
            new_state={"title": title, "status": "open"}
        )
        return request_id

def attach_evidence_to_request(request_id: int, evidence_id: int, actor_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO audit_request_evidence (request_id, evidence_id)
            VALUES (?, ?)
            """,
            (request_id, evidence_id),
        )
        
        # Update request status to 'in_review' if evidence is attached
        conn.execute(
            "UPDATE audit_requests SET status = 'in_review' WHERE id = ?",
            (request_id,)
        )
        
        log_audit_event(
            actor_id=actor_id,
            action="attach_evidence_to_pbc",
            object_type="audit_request",
            object_id=request_id,
            new_state={"evidence_id": evidence_id}
        )
