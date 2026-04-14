from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.db import get_connection
from app.services import (
    audit_service,
    controls_service,
    dashboard_service,
    evidence_service,
    task_service,
)


GRAPH_TYPE_LABELS = {
    "control": "Controls",
    "policy": "Policies",
    "document": "Documents",
    "risk": "Risk scenarios",
    "vendor": "Vendors",
    "audit": "Audits",
    "test": "Tests",
    "framework": "Frameworks",
    "integration": "Integrations",
    "task": "Tasks",
}


def _graph_object_payload(
    object_type: str,
    external_key: str,
    title: str,
    subtitle: str | None = None,
    description: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "object_type": object_type,
        "external_key": str(external_key),
        "title": title,
        "subtitle": subtitle,
        "description": description,
        "status": status,
        "owner": owner,
        "metadata_json": json.dumps(metadata or {}, default=str),
    }


def _upsert_graph_object(conn: sqlite3.Connection, payload: dict[str, Any]) -> int:
    conn.execute(
        """
        INSERT INTO graph_objects (
            object_type, external_key, title, subtitle, description, status, owner, metadata_json
        )
        VALUES (:object_type, :external_key, :title, :subtitle, :description, :status, :owner, :metadata_json)
        ON CONFLICT(object_type, external_key) DO UPDATE SET
            title = excluded.title,
            subtitle = excluded.subtitle,
            description = excluded.description,
            status = excluded.status,
            owner = excluded.owner,
            metadata_json = excluded.metadata_json,
            updated_at = datetime('now')
        """,
        payload,
    )
    row = conn.execute(
        """
        SELECT id
        FROM graph_objects
        WHERE object_type = ? AND external_key = ?
        """,
        (payload["object_type"], payload["external_key"]),
    ).fetchone()
    return int(row["id"])


def _graph_row_by_external_key(conn: sqlite3.Connection, object_type: str, external_key: str | int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT *
        FROM graph_objects
        WHERE object_type = ? AND external_key = ?
        """,
        (object_type, str(external_key)),
    ).fetchone()


def _link_exists(
    conn: sqlite3.Connection,
    left_type: str,
    left_id: int,
    right_type: str,
    right_id: int,
    link_type: str,
) -> bool:
    row = conn.execute(
        """
        SELECT id
        FROM graph_links
        WHERE link_type = ?
          AND (
            (left_type = ? AND left_id = ? AND right_type = ? AND right_id = ?)
            OR
            (left_type = ? AND left_id = ? AND right_type = ? AND right_id = ?)
          )
        """,
        (link_type, left_type, left_id, right_type, right_id, right_type, right_id, left_type, left_id),
    ).fetchone()
    return row is not None


def _ensure_graph_link(
    conn: sqlite3.Connection,
    left_type: str,
    left_id: int,
    right_type: str,
    right_id: int,
    link_type: str,
    notes: str | None = None,
) -> None:
    if _link_exists(conn, left_type, left_id, right_type, right_id, link_type):
        return
    conn.execute(
        """
        INSERT INTO graph_links (left_type, left_id, right_type, right_id, link_type, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (left_type, left_id, right_type, right_id, link_type, notes),
    )


def _graph_metadata(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    raw = row["metadata_json"] if isinstance(row, sqlite3.Row) else row.get("metadata_json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def sync_relationship_graph(statuses: list[dict[str, Any]] | None = None) -> None:
    controls = controls_service.list_controls()
    evidence = evidence_service.list_evidence()
    audits = audit_service.list_audits()
    risk_workspace = dashboard_service.get_risk_workspace()
    
    frameworks_by_id: dict[int, dict[str, Any]] = {}

    with get_connection() as conn:
        framework_rows = conn.execute(
            """
            SELECT id, name, version
            FROM frameworks
            ORDER BY id
            """
        ).fetchall()
        for framework in framework_rows:
            frameworks_by_id[int(framework["id"])] = dict(framework)
            _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "framework",
                    framework["id"],
                    framework["name"],
                    framework["version"],
                    f"{framework['name']} {framework['version']}",
                    "active",
                    None,
                    {
                        "framework_name": framework["name"],
                        "framework_version": framework["version"],
                    },
                ),
            )

        control_ids: dict[int, int] = {}
        test_ids: dict[int, int] = {}
        policy_ids: dict[int, int] = {}
        document_ids: dict[int, int] = {}
        risk_ids: dict[int, int] = {}
        audit_ids: dict[int, int] = {}
        vendor_ids: dict[str, int] = {}
        integration_ids: dict[str, int] = {}

        for control in controls:
            graph_id = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "control",
                    control["id"],
                    control["title"],
                    control["control_id"],
                    control["description"],
                    control["implementation_status"],
                    control["owner"],
                    {
                        "control_id": control["control_id"],
                        "type1_ready": bool(control["type1_ready"]),
                        "type2_ready": bool(control["type2_ready"]),
                        "last_tested_at": control["last_tested_at"],
                        "next_review_at": control["next_review_at"],
                    },
                ),
            )
            control_ids[int(control["id"])] = graph_id

            framework = frameworks_by_id.get(int(control.get("framework_id") or 1))
            if framework:
                framework_graph = _graph_row_by_external_key(conn, "framework", framework["id"])
                if framework_graph:
                    _ensure_graph_link(
                        conn,
                        "control",
                        graph_id,
                        "framework",
                        int(framework_graph["id"]),
                        "mapped_to",
                    )

            policy_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "policy",
                    control["id"],
                    f"{control['title']} Policy",
                    control["control_id"],
                    f"Policy backing {control['title'].lower()}.",
                    "approved" if control["implementation_status"] == "implemented" else "needs_review",
                    control["owner"],
                    {
                        "renewal_frequency": "annual",
                        "frameworks": ["SOC 2"],
                        "controls_count": 1,
                        "latest_version_label": "Approved",
                    },
                ),
            )
            policy_ids[int(control["id"])] = policy_graph
            _ensure_graph_link(conn, "control", graph_id, "policy", policy_graph, "depends_on")

            test_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "test",
                    control["id"],
                    f"{control['title']} Test",
                    control["control_id"],
                    f"Validation workflow for {control['title'].lower()}.",
                    "ok" if control["implementation_status"] == "implemented" else "attention",
                    control["owner"],
                    {
                        "integration_name": "Manual review",
                        "sla_days": 14,
                        "controls_count": 1,
                    },
                ),
            )
            test_ids[int(control["id"])] = test_graph
            _ensure_graph_link(conn, "control", graph_id, "test", test_graph, "validated_by")

        for item in evidence:
            document_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "document",
                    item["id"],
                    item["name"],
                    item["source"],
                    item.get("notes") or f"Evidence collected from {item['source']}.",
                    item["status"],
                    None,
                    {
                        "artifact_path": item["artifact_path"],
                        "collected_at": item["collected_at"],
                        "collection_due_date": item.get("collection_due_date"),
                        "audit_period_id": item.get("audit_period_id"),
                        "sharepoint_id": item.get("sharepoint_id"),
                        "type": "document",
                    },
                ),
            )
            document_ids[int(item["id"])] = document_graph
            control_graph_id = control_ids.get(int(item["control_id"]))
            if control_graph_id:
                _ensure_graph_link(conn, "control", control_graph_id, "document", document_graph, "evidenced_by")
                related_policy = policy_ids.get(int(item["control_id"]))
                if related_policy:
                    _ensure_graph_link(conn, "document", document_graph, "policy", related_policy, "supports")
                related_test = test_ids.get(int(item["control_id"]))
                if related_test:
                    _ensure_graph_link(conn, "test", related_test, "document", document_graph, "evidence")

        for risk in risk_workspace["risks"]:
            risk_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "risk",
                    risk["id"],
                    risk["title"],
                    risk["control_id"],
                    risk["reason"],
                    risk["status"],
                    risk["owner"],
                    {
                        "severity": risk["severity"],
                        "treatment_plan": "Mitigate",
                        "treatment_status": "incomplete",
                        "inherent_risk": 8 if risk["severity"] == "high" else 5,
                        "residual_risk": 4 if risk["severity"] == "high" else 2,
                        "category": "Compliance",
                        "source": "JEC Compliance Hub",
                    },
                ),
            )
            risk_ids[int(risk["id"])] = risk_graph
            control_graph_id = control_ids.get(int(risk["id"]))
            if control_graph_id:
                _ensure_graph_link(conn, "risk", risk_graph, "control", control_graph_id, "mitigated_by")
                test_graph = test_ids.get(int(risk["id"]))
                if test_graph:
                    _ensure_graph_link(conn, "risk", risk_graph, "test", test_graph, "monitored_by")
                policy_graph = policy_ids.get(int(risk["id"]))
                if policy_graph:
                    _ensure_graph_link(conn, "risk", risk_graph, "policy", policy_graph, "governed_by")

        for audit in audits:
            audit_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "audit",
                    audit["id"],
                    f"Audit: {audit['firm_name']}",
                    audit["type"].upper(),
                    audit.get("scope_notes") or "Audit scope and evidence readiness workspace.",
                    audit["status"],
                    None,
                    {
                        "firm_name": audit["firm_name"],
                        "audit_type": audit["type"],
                        "audit_period_id": audit["audit_period_id"],
                        "created_at": audit["created_at"],
                    },
                ),
            )
            audit_ids[int(audit["id"])] = audit_graph
            audit_control_rows = conn.execute(
                """
                SELECT control_id
                FROM audit_controls
                WHERE audit_id = ?
                """,
                (audit["id"],),
            ).fetchall()
            for row in audit_control_rows:
                control_graph_id = control_ids.get(int(row["control_id"]))
                if control_graph_id:
                    _ensure_graph_link(conn, "audit", audit_graph, "control", control_graph_id, "in_scope")

            finding_rows = conn.execute(
                """
                SELECT control_id
                FROM audit_findings
                WHERE audit_id = ?
                """,
                (audit["id"],),
            ).fetchall()
            for row in finding_rows:
                risk_graph = risk_ids.get(int(row["control_id"]))
                if risk_graph:
                    _ensure_graph_link(conn, "audit", audit_graph, "risk", risk_graph, "finding")

        for status in statuses or []:
            slug = status["source"].lower().replace(" ", "-")
            integration_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "integration",
                    slug,
                    status["source"],
                    "Connected source" if status["configured"] else "Needs setup",
                    status["detail"],
                    "connected" if status["configured"] else "review",
                    None,
                    {
                        "capabilities": _integration_capabilities_for_source(status["source"]),
                    },
                ),
            )
            integration_ids[slug] = integration_graph

            vendor_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "vendor",
                    slug,
                    status["source"],
                    "Integrated vendor",
                    status["detail"],
                    "active" if status["configured"] else "review",
                    None,
                    {
                        "category": "Cloud provider" if "microsoft" in slug or "azure" in slug else "SaaS provider",
                        "inherent_risk": "critical" if "azure" in slug else "medium",
                        "security_review_status": "up_to_date" if status["configured"] else "needs_review",
                    },
                ),
            )
            vendor_ids[slug] = vendor_graph
            _ensure_graph_link(conn, "vendor", vendor_graph, "integration", integration_graph, "powered_by")

            capabilities = _integration_capabilities_for_source(status["source"])
            if "documents" in capabilities:
                for document_graph in list(document_ids.values())[:3]:
                    _ensure_graph_link(conn, "integration", integration_graph, "document", document_graph, "feeds")
            if "policies" in capabilities:
                for policy_graph in list(policy_ids.values())[:3]:
                    _ensure_graph_link(conn, "integration", integration_graph, "policy", policy_graph, "feeds")
            if "task creation" in capabilities or "access" in capabilities:
                for test_graph in list(test_ids.values())[:2]:
                    _ensure_graph_link(conn, "integration", integration_graph, "test", test_graph, "supports")

        task_rows = task_service.list_tasks()
        for task in task_rows:
            task_graph = _upsert_graph_object(
                conn,
                _graph_object_payload(
                    "task",
                    task["id"],
                    task["title"],
                    task["type"],
                    task.get("description"),
                    task["status"],
                    None,
                    {
                        "priority": task["priority"],
                        "due_date": task["due_date"],
                    },
                ),
            )
            source_row = _graph_row_by_external_key(conn, task["source_object_type"], task["source_object_id"])
            if source_row:
                _ensure_graph_link(
                    conn,
                    task["source_object_type"],
                    int(source_row["id"]),
                    "task",
                    task_graph,
                    "tracked_by",
                )


def _integration_capabilities_for_source(source: str) -> list[str]:
    normalized = source.lower()
    capabilities: list[str] = []
    if "sharepoint" in normalized:
        capabilities.extend(["documents", "policies"])
    if any(token in normalized for token in ("jira", "monday", "notion")):
        capabilities.extend(["task creation", "access"])
    if any(token in normalized for token in ("azure", "defender", "intune", "github")):
        capabilities.extend(["access", "inventory", "vulnerabilities"])
    return capabilities or ["access"]


def list_graph_objects(object_type: str) -> list[dict[str, Any]]:
    sync_relationship_graph()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM graph_objects
            WHERE object_type = ?
            ORDER BY title COLLATE NOCASE
            """,
            (object_type,),
        ).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = _graph_metadata(row)
            items.append(item)
        return items


def _group_graph_links(conn: sqlite3.Connection, row: sqlite3.Row | dict[str, Any]) -> list[dict[str, Any]]:
    link_rows = conn.execute(
        """
        SELECT
            gl.id AS relationship_id,
            gl.link_type,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.id
                ELSE go_left.id
            END AS graph_id,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.object_type
                ELSE go_left.object_type
            END AS object_type,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.external_key
                ELSE go_left.external_key
            END AS external_key,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.title
                ELSE go_left.title
            END AS title,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.subtitle
                ELSE go_left.subtitle
            END AS subtitle,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.status
                ELSE go_left.status
            END AS status,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.owner
                ELSE go_left.owner
            END AS owner,
            CASE
                WHEN gl.left_type = ? AND gl.left_id = ? THEN go_right.metadata_json
                ELSE go_left.metadata_json
            END AS metadata_json
        FROM graph_links gl
        JOIN graph_objects go_left
          ON go_left.id = gl.left_id AND go_left.object_type = gl.left_type
        JOIN graph_objects go_right
          ON go_right.id = gl.right_id AND go_right.object_type = gl.right_type
        WHERE (gl.left_type = ? AND gl.left_id = ?)
           OR (gl.right_type = ? AND gl.right_id = ?)
        ORDER BY title COLLATE NOCASE
        """,
        (
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
            row["object_type"],
            row["id"],
        ),
    ).fetchall()

    grouped: dict[str, list[dict[str, Any]]] = {}
    for link in link_rows:
        object_type = str(link["object_type"])
        section = GRAPH_TYPE_LABELS.get(object_type, object_type.title())
        grouped.setdefault(section, []).append(
            {
                "relationship_id": int(link["relationship_id"]),
                "object_type": object_type,
                "external_key": str(link["external_key"]),
                "title": link["title"],
                "subtitle": link["subtitle"],
                "status": link["status"],
                "owner": link["owner"],
                "metadata": _graph_metadata(link),
                "link_type": link["link_type"],
            }
        )
    return [{"section": section, "items": items} for section, items in grouped.items()]


def get_graph_detail(object_type: str, external_key: str | int) -> dict[str, Any] | None:
    sync_relationship_graph()
    with get_connection() as conn:
        row = _graph_row_by_external_key(conn, object_type, external_key)
        if row is None:
            return None
        item = dict(row)
        item["metadata"] = _graph_metadata(row)
        item["mapped_elements"] = _group_graph_links(conn, row)

        if object_type == "audit":
            item["workspace"] = audit_service.get_audit_workspace(int(external_key))
        elif object_type == "control":
            item["evidence"] = evidence_service.list_evidence(int(external_key))
        elif object_type == "document":
            item["evidence"] = evidence_service.get_evidence(int(external_key))
        elif object_type == "vendor":
            item["recent_runs"] = dashboard_service.list_integration_runs(limit=6)
        elif object_type == "risk":
            item["tasks"] = [task for task in task_service.list_tasks() if task["source_object_type"] == "risk" and str(task["source_object_id"]) == str(external_key)]
        return item


def list_graph_link_options(object_type: str) -> list[dict[str, Any]]:
    sync_relationship_graph()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT object_type, external_key, title, subtitle, status
            FROM graph_objects
            WHERE object_type <> ?
            ORDER BY object_type, title COLLATE NOCASE
            """,
            (object_type,),
        ).fetchall()
        return [dict(row) for row in rows]


def create_graph_relationship(
    source_type: str,
    source_key: str | int,
    target_type: str,
    target_key: str | int,
    link_type: str | None = None,
) -> dict[str, Any]:
    sync_relationship_graph()
    resolved_link_type = link_type or "linked_to"
    with get_connection() as conn:
        source = _graph_row_by_external_key(conn, source_type, source_key)
        target = _graph_row_by_external_key(conn, target_type, target_key)
        if source is None or target is None:
            raise ValueError("Relationship endpoint could not resolve one or both objects")
        if source["object_type"] == target["object_type"] and source["external_key"] == target["external_key"]:
            raise ValueError("Cannot link an object to itself")
        _ensure_graph_link(
            conn,
            str(source["object_type"]),
            int(source["id"]),
            str(target["object_type"]),
            int(target["id"]),
            resolved_link_type,
        )
    detail = get_graph_detail(source_type, source_key)
    if detail is None:
        raise ValueError("Unable to load updated relationship graph")
    return detail


def delete_graph_relationship(relationship_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            DELETE FROM graph_links
            WHERE id = ?
            """,
            (relationship_id,),
        )
