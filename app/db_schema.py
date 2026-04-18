# --- IMMUTABLE SQL BOOTSTRAP ---
# This contains the core SOC 2 schema for the JEC Compliance Hub.

BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS frameworks (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS controls (
    id SERIAL PRIMARY KEY,
    framework_id INTEGER NOT NULL,
    control_id TEXT NOT NULL,
    control_code TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT,
    owner TEXT,
    owner_user_id INTEGER,
    implementation_status TEXT NOT NULL DEFAULT 'draft',
    frequency TEXT DEFAULT 'manual',
    is_automated INTEGER NOT NULL DEFAULT 0,
    type1_status TEXT NOT NULL DEFAULT 'not_started',
    type2_status TEXT NOT NULL DEFAULT 'not_started',
    type1_ready INTEGER NOT NULL DEFAULT 0,
    type2_ready INTEGER NOT NULL DEFAULT 0,
    last_tested_at TEXT,
    next_review_at TEXT,
    next_review_date TEXT,
    evidence_requirements TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY(framework_id) REFERENCES frameworks(id) ON DELETE CASCADE,
    FOREIGN KEY(owner_user_id) REFERENCES users(id),
    UNIQUE(framework_id, control_id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id SERIAL PRIMARY KEY,
    control_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted',
    uploaded_by INTEGER,
    reviewed_by INTEGER,
    rejection_reason TEXT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    sha256_hash TEXT,
    sharepoint_url TEXT,
    sharepoint_item_id TEXT,
    local_path TEXT,
    file_name TEXT,
    file_size_bytes INTEGER,
    mime_type TEXT,
    locked_at TEXT,
    locked_by INTEGER,
    audit_period_id INTEGER,
    collection_due_date TEXT,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
    FOREIGN KEY(uploaded_by) REFERENCES users(id),
    FOREIGN KEY(reviewed_by) REFERENCES users(id),
    FOREIGN KEY(locked_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS control_checks (
    id SERIAL PRIMARY KEY,
    control_id INTEGER NOT NULL,
    checked_at TEXT NOT NULL,
    result TEXT NOT NULL,
    details TEXT NOT NULL,
    FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS integration_runs (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS integration_snapshots (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    snapshot_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    collected_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    oid TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'viewer',
    scoped_token TEXT UNIQUE,
    token_expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_requests (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    control_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    requested_by INTEGER,
    created_by INTEGER,
    assigned_to INTEGER,
    request_type TEXT DEFAULT 'evidence_request',
    sample_size INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(requested_by) REFERENCES users(id),
    FOREIGN KEY(created_by) REFERENCES users(id),
    FOREIGN KEY(assigned_to) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_request_evidence (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL,
    evidence_id INTEGER NOT NULL,
    attached_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    attached_at TEXT,
    UNIQUE(request_id, evidence_id),
    FOREIGN KEY(request_id) REFERENCES audit_requests(id) ON DELETE CASCADE,
    FOREIGN KEY(evidence_id) REFERENCES evidence(id) ON DELETE CASCADE,
    FOREIGN KEY(attached_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    actor_id INTEGER,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id INTEGER NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(actor_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_periods (
    id SERIAL PRIMARY KEY,
    framework_id INTEGER,
    name TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    type TEXT,
    report_type TEXT,
    observation_start TEXT,
    observation_end TEXT,
    point_in_time_date TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(framework_id) REFERENCES frameworks(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    source_object_type TEXT NOT NULL,
    source_object_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    owner_id INTEGER,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY(owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audits (
    id SERIAL PRIMARY KEY,
    audit_period_id INTEGER,
    period_id INTEGER,
    type TEXT,
    firm_name TEXT,
    audit_firm TEXT,
    status TEXT NOT NULL DEFAULT 'preparation',
    scope_notes TEXT,
    early_access_date TEXT,
    fieldwork_start TEXT,
    fieldwork_end TEXT,
    report_date TEXT,
    lead_auditor_email TEXT,
    notes TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    closed_at TEXT,
    FOREIGN KEY(audit_period_id) REFERENCES audit_periods(id),
    FOREIGN KEY(period_id) REFERENCES audit_periods(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_controls (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    control_id INTEGER NOT NULL,
    evidence_status TEXT NOT NULL DEFAULT 'missing',
    assigned_to INTEGER,
    notes TEXT,
    in_scope INTEGER NOT NULL DEFAULT 1,
    auditor_notes TEXT,
    UNIQUE(audit_id, control_id),
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
    FOREIGN KEY(assigned_to) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_findings (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    control_id INTEGER,
    finding_type TEXT,
    title TEXT NOT NULL,
    description TEXT,
    management_response TEXT,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    owner_id INTEGER,
    due_date TEXT,
    closed_at TEXT,
    remediation_notes TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
    FOREIGN KEY(owner_id) REFERENCES users(id),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_users (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
    assigned_by INTEGER,
    access_expires_at TEXT,
    UNIQUE(audit_id, user_id),
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(assigned_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_comments (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    request_id INTEGER,
    evidence_id INTEGER,
    parent_id INTEGER,
    author_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    is_internal INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(request_id) REFERENCES audit_requests(id) ON DELETE CASCADE,
    FOREIGN KEY(evidence_id) REFERENCES evidence(id),
    FOREIGN KEY(parent_id) REFERENCES audit_comments(id),
    FOREIGN KEY(author_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS readiness_snapshots (
    id SERIAL PRIMARY KEY,
    audit_period_id INTEGER NOT NULL,
    report_type TEXT NOT NULL,
    calculated_at TEXT NOT NULL DEFAULT (datetime('now')),
    calculated_by INTEGER,
    overall_score NUMERIC,
    controls_ready INTEGER NOT NULL DEFAULT 0,
    controls_partial INTEGER NOT NULL DEFAULT 0,
    controls_not_ready INTEGER NOT NULL DEFAULT 0,
    controls_not_applicable INTEGER NOT NULL DEFAULT 0,
    summary_json TEXT NOT NULL,
    FOREIGN KEY(audit_period_id) REFERENCES audit_periods(id) ON DELETE CASCADE,
    FOREIGN KEY(calculated_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS readiness_gaps (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL,
    control_id INTEGER NOT NULL,
    gap_type TEXT NOT NULL,
    gap_start TEXT,
    gap_end TEXT,
    severity TEXT NOT NULL,
    detail TEXT NOT NULL,
    FOREIGN KEY(snapshot_id) REFERENCES readiness_snapshots(id) ON DELETE CASCADE,
    FOREIGN KEY(control_id) REFERENCES controls(id)
);

CREATE TABLE IF NOT EXISTS evidence_controls (
    id SERIAL PRIMARY KEY,
    evidence_id INTEGER NOT NULL,
    control_id INTEGER NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(evidence_id, control_id),
    FOREIGN KEY(evidence_id) REFERENCES evidence(id) ON DELETE CASCADE,
    FOREIGN KEY(control_id) REFERENCES controls(id)
);

CREATE TABLE IF NOT EXISTS graph_objects (
    id SERIAL PRIMARY KEY,
    object_type TEXT NOT NULL,
    external_key TEXT NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT,
    description TEXT,
    status TEXT,
    owner TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(object_type, external_key)
);

CREATE TABLE IF NOT EXISTS graph_links (
    id SERIAL PRIMARY KEY,
    left_type TEXT NOT NULL,
    left_id INTEGER NOT NULL,
    right_type TEXT NOT NULL,
    right_id INTEGER NOT NULL,
    link_type TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(left_type, left_id, right_type, right_id, link_type)
);
"""
