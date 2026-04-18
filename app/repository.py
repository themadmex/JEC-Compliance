from __future__ import annotations

from app.services.controls_service import (
    DEFAULT_FRAMEWORK_NAME,
    DEFAULT_FRAMEWORK_VERSION,
    _ensure_framework,
    list_controls,
    get_control,
    create_control,
    update_control_status,
)
from app.services.evidence_service import (
    EVIDENCE_STALE_DAYS,
    LOCKED_ARTIFACTS_DIR,
    list_evidence,
    get_evidence,
    create_evidence,
    approve_evidence,
    reject_evidence,
    lock_evidence,
    run_evidence_health_check,
    get_documents_workspace,
)
from app.services.audit_service import (
    EXPORTS_DIR,
    list_audits,
    list_audits_for_auditor,
    create_audit,
    get_audit,
    update_audit,
    update_audit_control,
    assign_auditor,
    list_audit_auditors,
    remove_auditor,
    auditor_has_scope,
    get_auditor_portal,
    create_audit_finding,
    update_audit_finding,
    get_audit_finding,
    get_audit_workspace,
    export_audit_packet,
    list_audit_periods,
    create_audit_period,
    calculate_readiness,
    list_audit_requests,
    create_request,
    get_request,
    update_request,
    scan_overdue_audit_requests,
    attach_request_evidence,
    add_request_comment,
)
from app.services.task_service import (
    list_tasks,
    create_task,
    get_task,
    update_task_status,
)
from app.services.user_service import upsert_user, list_auditor_users
from app.services.dashboard_service import (
    get_readiness_summary,
    get_dashboard_summary,
    get_gap_report,
    get_phase1_overview,
    list_integration_runs,
    log_integration_run,
)
from app.services.log_service import log_audit_event
from app.services.graph_service import (
    GRAPH_TYPE_LABELS,
    sync_relationship_graph,
    list_graph_objects,
    get_graph_detail,
    list_graph_link_options,
    create_graph_relationship,
    delete_graph_relationship,
)


def get_default_control_id() -> int | None:
    controls = list_controls()
    return int(controls[0]["id"]) if controls else None


def get_audits_workspace():
    from app.services.dashboard_service import get_audits_workspace
    return get_audits_workspace()


def get_risk_workspace():
    from app.services.dashboard_service import get_risk_workspace
    return get_risk_workspace()


def get_policy_workspace():
    from app.services.dashboard_service import get_policy_workspace
    return get_policy_workspace()


def get_vendor_workspace(statuses):
    from app.services.dashboard_service import get_vendor_workspace
    return get_vendor_workspace(statuses)


def get_trust_workspace():
    from app.services.dashboard_service import get_trust_workspace
    return get_trust_workspace()
