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
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    owner TEXT,
    implementation_status TEXT NOT NULL DEFAULT 'draft',
    type1_ready INTEGER NOT NULL DEFAULT 0,
    type2_ready INTEGER NOT NULL DEFAULT 0,
    last_tested_at TEXT,
    next_review_at TEXT,
    FOREIGN KEY(framework_id) REFERENCES frameworks(id) ON DELETE CASCADE,
    UNIQUE(framework_id, control_id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id SERIAL PRIMARY KEY,
    control_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    source TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    status TEXT NOT NULL DEFAULT 'accepted',
    notes TEXT,
    submitter_id INTEGER,
    approver_id INTEGER,
    approved_at TEXT,
    rejected_reason TEXT,
    locked_at TEXT,
    sha256_hash TEXT,
    sharepoint_id TEXT,
    audit_period_id INTEGER,
    collection_due_date TEXT,
    FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE
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
    collected_at TEXT NOT NULL DEFAULT (now())
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    oid TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'viewer',
    scoped_token TEXT UNIQUE,
    token_expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (now()),
    last_login_at TEXT NOT NULL DEFAULT (now())
);

CREATE TABLE IF NOT EXISTS audit_requests (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    control_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    requested_by INTEGER NOT NULL,
    assigned_to INTEGER,
    created_at TEXT NOT NULL DEFAULT (now()),
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(requested_by) REFERENCES users(id),
    FOREIGN KEY(assigned_to) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_request_evidence (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL,
    evidence_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (now()),
    UNIQUE(request_id, evidence_id),
    FOREIGN KEY(request_id) REFERENCES audit_requests(id) ON DELETE CASCADE,
    FOREIGN KEY(evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    actor_id INTEGER,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id INTEGER NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    created_at TEXT NOT NULL DEFAULT (now()),
    FOREIGN KEY(actor_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_periods (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    type TEXT NOT NULL,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (now()),
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    source_object_type TEXT NOT NULL,
    source_object_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL DEFAULT (now()),
    completed_at TEXT,
    FOREIGN KEY(owner_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audits (
    id SERIAL PRIMARY KEY,
    audit_period_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    firm_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    scope_notes TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (now()),
    closed_at TEXT,
    FOREIGN KEY(created_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_controls (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    control_id INTEGER NOT NULL,
    evidence_status TEXT NOT NULL DEFAULT 'missing',
    assigned_to INTEGER,
    notes TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
    FOREIGN KEY(assigned_to) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_findings (
    id SERIAL PRIMARY KEY,
    audit_id INTEGER NOT NULL,
    control_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    owner_id INTEGER NOT NULL,
    due_date TEXT,
    closed_at TEXT,
    remediation_notes TEXT,
    FOREIGN KEY(audit_id) REFERENCES audits(id) ON DELETE CASCADE,
    FOREIGN KEY(control_id) REFERENCES controls(id) ON DELETE CASCADE,
    FOREIGN KEY(owner_id) REFERENCES users(id)
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
    created_at TEXT NOT NULL DEFAULT (now()),
    updated_at TEXT NOT NULL DEFAULT (now()),
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
    created_at TEXT NOT NULL DEFAULT (now()),
    UNIQUE(left_type, left_id, right_type, right_id, link_type)
);
"""
