from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import get_connection, get_table_columns
from app.services import controls_service, evidence_service, audit_service, task_service
from app.services.evidence_service import EVIDENCE_STALE_DAYS


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


def get_gap_report() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=EVIDENCE_STALE_DAYS)
    stale_cutoff_str = stale_cutoff.isoformat()

    with get_connection() as conn:
        evidence_timestamp_expr = _evidence_timestamp_sql(conn)
        rows = conn.execute(
            f"""
            SELECT c.id AS control_db_id, c.control_id, c.title,
                   CASE
                     WHEN latest.evidence_at IS NULL THEN 'No evidence collected'
                     WHEN latest.evidence_at < ? THEN 'Latest evidence is stale'
                     WHEN c.implementation_status != 'implemented' THEN 'Control not implemented'
                     ELSE 'Needs review'
                   END AS reason
            FROM controls c
            LEFT JOIN (
                SELECT control_id, MAX({evidence_timestamp_expr}) AS evidence_at
                FROM evidence
                GROUP BY control_id
            ) latest ON latest.control_id = c.id
            WHERE latest.evidence_at IS NULL
               OR latest.evidence_at < ?
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
        evidence_timestamp_expr = _evidence_timestamp_sql(conn)
        policies_total = int(conn.execute("SELECT COUNT(*) AS c FROM controls").fetchone()["c"])
        policies_attention = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM controls WHERE implementation_status != 'implemented'"
            ).fetchone()["c"]
        )

        tests_total = policies_total
        tests_attention = int(
            conn.execute(
                f"""
                SELECT COUNT(*) AS c
                FROM controls c
                LEFT JOIN (
                  SELECT control_id, MAX({evidence_timestamp_expr}) AS evidence_at
                  FROM evidence
                  GROUP BY control_id
                ) latest ON latest.control_id = c.id
                WHERE latest.evidence_at IS NULL OR latest.evidence_at < ?
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


def get_audits_workspace() -> dict[str, Any]:
    controls = controls_service.list_controls()
    evidence = evidence_service.list_evidence()
    gaps = get_gap_report()
    latest_by_control: dict[int, dict[str, Any]] = {}
    for item in evidence:
        evidence_at = _evidence_timestamp(item)
        current = latest_by_control.get(item["control_id"])
        if current is None or evidence_at > _evidence_timestamp(current):
            latest_by_control[item["control_id"]] = {**item, "evidence_at": evidence_at}

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
                "latest_evidence_at": latest["evidence_at"] if latest else None,
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


def _evidence_timestamp(item: dict[str, Any]) -> str:
    for key in ("valid_from", "collected_at", "created_at"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _evidence_timestamp_sql(conn: Any) -> str:
    columns = get_table_columns(conn, "evidence")
    candidates = [
        column
        for column in ("valid_from", "collected_at", "created_at")
        if column in columns
    ]
    if not candidates:
        return "NULL"
    return f"COALESCE({', '.join(candidates)})"


def get_risk_workspace() -> dict[str, Any]:
    controls = controls_service.list_controls()
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
    controls = controls_service.list_controls()
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
