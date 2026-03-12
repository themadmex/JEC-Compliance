from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import get_connection
from app.schemas import ControlCreate, EvidenceCreate


DEFAULT_FRAMEWORK_NAME = "SOC 2"
DEFAULT_FRAMEWORK_VERSION = "2017 TSC"
EVIDENCE_STALE_DAYS = 90


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
                       period_start, period_end, status, notes
                FROM evidence
                ORDER BY collected_at DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, control_id, name, source, artifact_path, collected_at,
                       period_start, period_end, status, notes
                FROM evidence
                WHERE control_id = ?
                ORDER BY collected_at DESC
                """,
                (control_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def create_evidence(payload: EvidenceCreate) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO evidence (
                control_id, name, source, artifact_path, collected_at,
                period_start, period_end, status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        new_id = int(cursor.lastrowid)
        row = conn.execute(
            """
            SELECT id, control_id, name, source, artifact_path, collected_at,
                   period_start, period_end, status, notes
            FROM evidence
            WHERE id = ?
            """,
            (new_id,),
        ).fetchone()
        return dict(row)


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
