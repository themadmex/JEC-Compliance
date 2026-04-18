# JEC Compliance Engine
## Product Requirements Document v2.4

**Status:** Final - Source of Truth  
**Owner:** Jean Edwards Consulting - Engineering  
**Stack Lock:** FastAPI | SQLAlchemy | Alembic | APScheduler | SQLite/PostgreSQL | Static HTML/JS | Microsoft Entra ID | SharePoint/Graph  
**Do Not Use:** Node.js | Next.js | tRPC | BullMQ | NextAuth  
**Supersedes:** PRD v2.3

---

## Changelog

### v2.4 (current)
| # | Topic | Change |
|---|---|---|
| 1 | Compliance Agent analysis | Added honest assessment of Vanta Compliance Agent (March 2026) against JEC scope |
| 2 | Section 14.4 | Clarified which Compliance Agent capabilities are out of scope (AI-driven) vs achievable without AI (rule-based service account detection, policy-vs-control consistency flagging) |
| 3 | Phase 2 backlog | Added service account detection rule to check engine |
| 4 | Phase 3b backlog | Added policy-vs-control consistency check to policy management phase |
| 5 | Auditor access management | Recorded completed implementation: `GET /api/v1/auditors`, `GET /api/v1/audits/{id}/auditors`, scoped_token generation on assignment, portal link, revoke 404 + audit log |
| 6 | Architecture Decision 5.7 | Token-vs-scope separation documented as resolved design decision |
| 7 | users table | Added `scoped_token` and `token_expires_at` columns; documented transitional `oid`/`name` compatibility with `entra_oid`/`display_name` |
| 8 | Phase status | Marked completed Phase 5/6 auditor-access and PBC items that are covered by the live implementation and tests |
| 9 | Phase 6 handoff | Added daily PBC overdue scanner, scheduler job, and test coverage so Phase 6 can hand over to Phase 7 |
| 10 | Phase 7 readiness engines | Added persisted Type I/Type II readiness calculations, gap rows, and export snapshot verification |

### v2.3
| # | Topic | Change |
|---|---|---|
| 1 | Vanta gap analysis | Added Section 5.6 (read-only API principle), Section 6.5 (evidence-to-multiple-controls via `evidence_controls` junction table), Section 6.6 (policies table), Section 6.7 (access reviews), Section 6.8 (personnel compliance), Section 6.9 (risk register) |
| 2 | New phases | Added Phase 3b (Policy Management), Phase 3c (Access Reviews), Phase 3d (Personnel Compliance), Phase 3e (Risk Register) |
| 3 | New pages | Added 6 new frontend pages for policies, access reviews, personnel, risk register, notifications, and employee portal |
| 4 | Roadmap | Expanded Section 14 with all Vanta-equivalent gaps and their priority |
| 5 | Scope note | Added honest Vanta-parity statement to Section 1 |

### v2.2
| # | Topic | Change |
|---|---|---|
| 1 | Encoding | Replaced all non-ASCII Unicode with ASCII equivalents: em dash -> `-`, middle dot -> `|`, arrows -> `->`, multiplication sign -> `x`, box-drawing chars -> `-`. File is now pure ASCII. |
| 2 | Phase 1 constraints | Added explicit data-migration rule: existing data must be migrated forward; destructive schema resets require explicit approval |

### v2.1
| # | Topic | Change |
|---|---|---|
| 1 | Primary keys | Clarified: keep existing integer IDs; UUID adoption is a future decision |
| 2 | API route prefix | Explicit strategy: `/api/v1/` for all new routes; old paths preserved as compatibility aliases |
| 3 | SQLAlchemy migration path | New tables use declarative models; existing raw SQL untouched until the code is modified |
| 4 | SharePoint signed URLs | Softened to tenant-policy-aware language |
| 5 | Type II data model | Added `readiness_snapshots` and `readiness_gaps` tables |
| 6 | SOC 2 control set | Explicit disclaimer: 10 controls are an MVP starter set, not audit-sufficient |
| 7 | Audit log immutability | Clarified: application-level append-only now; WORM hardening deferred |
| 8 | auth.py | Existing file noted as in-progress; Phase 1 must not break it |

---

## 1. Purpose

The JEC Compliance Engine is an internal SOC 2 Type I and Type II readiness platform for Jean Edwards Consulting. It replaces manual spreadsheet compliance tracking with a purpose-built system modeled on Vanta's engagement workflow - self-hosted, backed by the firm's Microsoft 365/SharePoint infrastructure, and implemented entirely on the existing FastAPI stack.

The platform covers the full compliance lifecycle:

> Control inventory -> Automated checks -> Evidence collection -> Evidence approval/locking -> Audit engagement -> Auditor portal -> PBC request workflow -> Type I snapshot -> Type II operating-effectiveness analysis -> Audit packet export

**Vanta-parity scope note:** This platform implements the core Vanta compliance workflow for SOC 2 using periodic automated checks and five integration providers rather than Vanta's real-time streaming model and 400+ connectors. The features listed above place JEC at rough functional parity with Vanta's audit, evidence, and auditor-portal workflows. The following Vanta capabilities are implemented in later phases (see Section 14): policy template management, structured access reviews, personnel and device compliance tracking, risk register, and a notification system. The following are explicitly out of scope for this product: AI questionnaire automation, public trust center, multi-framework support beyond SOC 2, third-party risk management portal, and multi-tenant billing.

---

## 2. Goals and Non-Goals

### Goals
- Maintain a live SOC 2 control inventory with ownership, frequency, and readiness state
- Run automated control checks on a schedule and surface failures as remediation tasks
- Collect, approve, hash, lock, and export evidence backed by SharePoint
- Manage audit engagements (firm, window, scope, auditor access)
- Provide auditors a scoped read-only portal for their assigned engagement
- Support PBC / custom evidence requests with threaded comments
- Produce real Type I point-in-time readiness and Type II operating-effectiveness analysis
- Log every sensitive action for an immutable audit trail

### Non-Goals (deferred)
- Public trust center
- Multi-tenant SaaS or billing
- AI chatbot or AI-assisted gap analysis
- Mobile app
- Non-SOC 2 frameworks (HIPAA, ISO 27001, etc.) before SOC 2 is complete
- Vendor risk management module
- Multi-org support
- WORM / storage-level audit log immutability (application-level append-only rules are sufficient for now)

---

## 3. Users and Roles

| Role | Description | Key Permissions |
|---|---|---|
| **Compliance Manager** | Owns readiness, controls, audits, evidence, auditor workflow | Full internal access; approve/reject/lock evidence; create audits; assign auditors |
| **Control Owner** | Resolves assigned controls, uploads evidence, handles remediation tasks | View/upload evidence for owned controls; manage assigned tasks |
| **Security Reviewer** | Reviews controls, findings, and evidence quality | Read all controls and evidence; add internal comments; cannot approve/lock |
| **Auditor** | External; scoped read-only access to one engagement | View controls and evidence in scope and within audit window only |
| **Viewer** | Internal read-only | View dashboard, controls, evidence; no write access |

All roles are enforced server-side on every route. Auditor access is further restricted by engagement scope and expires when the audit is marked complete.

---

## 4. Tech Stack (Frozen)

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI |
| ORM | SQLAlchemy - new tables use declarative models; existing raw SQL repository patterns remain until the relevant code is modified |
| Migrations | Alembic |
| Database - dev | SQLite |
| Database - prod | PostgreSQL 16 |
| Scheduler | APScheduler (in-process, FastAPI lifespan) |
| Queue/cache | Redis available in docker-compose; not used for job queuing yet |
| Frontend | Static HTML + CSS + Vanilla JavaScript served by FastAPI StaticFiles |
| Auth | Microsoft Entra ID / MSAL; session cookie; RBAC middleware |
| File storage | SharePoint / Microsoft Graph (primary); local filesystem fallback for dev |
| Deployment | Internal web app/API; Docker Compose |

---

## 5. Architecture Decisions

This section captures decisions that must be settled before Phase 1 implementation begins. They are recorded here as the resolved position so the team has a single reference.

### 5.1 Primary Keys - Integer IDs

**Decision: Keep existing integer SERIAL / SQLite integer primary keys.**

The current app uses integer IDs throughout its models and raw SQL repositories. Migrating to UUIDs would require rewriting all repository queries, all foreign key columns, and all existing data - a high-risk change with no functional benefit at this stage.

**Rules:**
- All new tables use integer SERIAL (PostgreSQL) / INTEGER AUTOINCREMENT (SQLite) primary keys
- UUID adoption may be revisited as a future schema hardening item if the app ever needs to federate data across instances
- Do not mix UUID and integer PKs in new foreign key relationships

### 5.2 API Route Prefix Strategy

**Decision: `/api/v1/` prefix on all new routes; existing routes preserved as compatibility aliases.**

The current app has mixed paths (`/controls`, `/evidence`, `/dashboard`, `/integrations`, some `/api/...`). Forcing a big-bang rename would break the existing frontend before it is updated.

**Rules:**
- All routes introduced in Phase 2 and later live under `/api/v1/`
- Existing routes outside `/api/v1/` are kept as-is and documented as compatibility aliases
- The frontend is updated to call `/api/v1/` endpoints as each page is rebuilt in Phase 8
- Compatibility aliases are removed only when no frontend page still references them
- The OpenAPI docs at `/docs` show both old and new routes until aliases are retired

### 5.3 SQLAlchemy Migration Path

**Decision: Incremental adoption, not a full rewrite.**

The current app uses raw SQL repository patterns in several places. Forcing an immediate rewrite to SQLAlchemy declarative models would stall Phase 1.

**Rules:**
- Every new table introduced by this PRD must use a SQLAlchemy declarative model in `app/models/`
- Existing raw SQL repositories may remain until the team touches that code for another reason
- New code that needs to JOIN against an existing raw-SQL table may use SQLAlchemy `text()` or a mixed query - this is acceptable
- The goal is that by Phase 7, all tables have models; by Phase 10, no raw SQL strings exist in route handlers

### 5.4 auth.py - In-Progress File

**The repo already has a modified `auth.py`. Phase 1 must not break it.**

- Do not rename, move, or restructure `auth.py` in Phase 1
- If Phase 1 schema changes affect the `users` table, coordinate with whoever owns `auth.py`
- Session and MSAL logic in `auth.py` is the authoritative implementation; the PRD's auth description describes intended behavior, not a mandate to rewrite what already exists

### 5.5 Audit Log Immutability Scope

**Application-level append-only is the current requirement. WORM/storage-level immutability is deferred.**

Concretely this means:
- No `UPDATE` or `DELETE` statements may reference the `audit_log` table anywhere in application code
- The Alembic migration for `audit_log` must not define `ON DELETE CASCADE` or `ON UPDATE CASCADE` on any FK
- Code review must reject any PR that modifies existing audit log rows
- WORM bucket / database-level append-only enforcement is a future hardening item listed in the roadmap

### 5.6 Integration Read-Only Principle

**All integrations use read-only API access. The system never writes to external tools.**

This mirrors how Vanta operates and is a security and trust requirement for this platform.

Concretely:
- Google Workspace: service account has read-only Admin SDK scopes; it cannot modify users, suspend accounts, or change roles
- GitHub: token has `repo:read`, `org:read` scopes only; it cannot push code, modify branch protection, or close issues
- AWS: IAM role has a read-only policy (e.g., `SecurityAudit` managed policy); it cannot modify resources
- Okta: API token is scoped to read-only; it cannot deprovision users or modify group memberships
- SharePoint: the only write operation permitted is uploading evidence files to the designated compliance folder

The only write capability the system has toward external tools is creating remediation tickets in a ticketing system if that integration is added in a future phase. That capability must be explicitly opt-in per configuration.

Any integration code that performs a write operation against an external system other than SharePoint evidence upload must be rejected in code review.

### 5.7 Auditor Token vs Audit Scope - Resolved Design Decision

**Decision: auditor tokens are user-level credentials; audit scope is an authorization check performed on every request.**

These are intentionally separate concerns. Implemented in Phase 5 / Phase 6 hardening.

**How it works:**
- When an auditor is assigned to an audit, the system checks whether that user already has a `scoped_token` in the `users` table. If not, one is generated and stored.
- The `scoped_token` is a credential that proves the holder is an auditor who has been invited to the platform. It is user-level, not audit-level.
- Audit scope (which controls, evidence, and requests an auditor may see) is enforced on every request by the `require_audit_scope(audit_id)` dependency, which checks the `audit_users` table.
- Revoking an auditor from one audit deletes their `audit_users` row for that audit. Their `scoped_token` remains valid. If they are still assigned to another audit, they retain access to that audit only.
- If an auditor is removed from all audits, their token still exists but every request will fail the `require_audit_scope` check and return 403. There is no content they can reach.
- The portal link shown in the audit detail UI is currently constructed as `/?token={scoped_token}#auditor-portal`. The token identifies the auditor; the portal then lists assigned audits. It is not a signed URL with embedded scope; scope is always checked server-side on each audit request.

**Why this is correct:**
- A credential (token) answers "are you who you say you are?"
- Authorization (scope check) answers "are you allowed to see this?"
- Conflating the two would require invalidating and regenerating tokens every time an auditor's scope changes, which creates race conditions and complicates the audit trail.

**Security implications (recorded for code review):**
- A revoked-from-one-audit auditor with an active token and remaining audit assignments can still use the same token. This is by design.
- A fully-removed auditor (no `audit_users` rows) cannot reach any content despite holding a valid token. The 403 is enforced by `require_audit_scope`, not by token invalidation.
- If the security requirement ever changes to "token must be invalidated on any revocation", the `scoped_token` column can be set to NULL on full removal without changing the scope enforcement logic.

---

## 6. Data Model

### 6.1 Primary Key Convention

All tables use:
- **PostgreSQL:** `id SERIAL PRIMARY KEY` (auto-incrementing integer)
- **SQLite:** `id INTEGER PRIMARY KEY AUTOINCREMENT`

Foreign key columns reference integer IDs (`INTEGER` type, not UUID).

### 6.2 Core Tables

#### `frameworks`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT NOT NULL | e.g., "SOC 2" |
| version | TEXT | |
| description | TEXT | |
| created_at | TIMESTAMP | default now() |

#### `controls`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| framework_id | FK -> frameworks.id | |
| control_code | TEXT UNIQUE NOT NULL | e.g., CC6.1 |
| title | TEXT NOT NULL | |
| description | TEXT | |
| category | TEXT | Trust Service Criterion label |
| owner_user_id | FK -> users.id | nullable |
| frequency | TEXT | see frequency enum below |
| is_automated | BOOLEAN | default false |
| type1_status | TEXT | see status enum below; default 'not_started' |
| type2_status | TEXT | see status enum below; default 'not_started' |
| next_review_date | DATE | nullable |
| evidence_requirements | TEXT | human-readable description |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | updated on every write |

Frequency values: `continuous`, `daily`, `weekly`, `monthly`, `quarterly`, `annual`, `on_change`, `manual`  
Type1 status values: `not_started`, `in_progress`, `implemented`, `not_applicable`  
Type2 status values: `not_started`, `in_progress`, `operating`, `failing`, `not_applicable`

#### `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| entra_oid | TEXT UNIQUE | Microsoft Entra object ID; nullable until first login |
| email | TEXT UNIQUE NOT NULL | |
| display_name | TEXT | |
| role | TEXT NOT NULL | see role enum in Section 3 |
| is_active | BOOLEAN | default true |
| scoped_token | TEXT UNIQUE | nullable; generated on first auditor assignment; user-level credential; see Section 5.7 |
| token_expires_at | TIMESTAMP | nullable; updated from the auditor assignment expiry; checked when authenticating `X-Auditor-Token` |
| created_at | TIMESTAMP | default now() |
| last_login | TIMESTAMP | nullable |

**Transitional compatibility note:** the legacy auth path still reads `oid`, `name`, and `last_login_at`. The Phase 1 migration added `entra_oid` and `display_name` for forward compatibility, but `oid`/`name` remain live application columns until `auth.py` and user repository code are migrated.

#### `evidence`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| control_id | FK -> controls.id | |
| title | TEXT NOT NULL | |
| description | TEXT | |
| source_type | TEXT | `manual`, `integration`, `policy`, `system_generated` |
| status | TEXT | see evidence status enum below; default 'submitted' |
| uploaded_by | FK -> users.id | |
| reviewed_by | FK -> users.id | nullable |
| rejection_reason | TEXT | nullable; required when status='rejected' |
| valid_from | DATE NOT NULL | |
| valid_to | DATE | nullable; null = no expiry |
| sha256_hash | TEXT | computed at upload; verified at lock |
| sharepoint_url | TEXT | nullable |
| sharepoint_item_id | TEXT | nullable |
| local_path | TEXT | nullable; dev fallback only; never used in production |
| file_name | TEXT NOT NULL | original filename; display only; never used in file paths |
| file_size_bytes | INTEGER | |
| mime_type | TEXT | |
| locked_at | TIMESTAMP | nullable |
| locked_by | FK -> users.id | nullable |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | updated on every write |

Evidence status values: `submitted`, `accepted`, `rejected`, `locked`, `stale`, `expired`, `flagged`, `not_applicable`

#### `control_checks`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| control_id | FK -> controls.id | |
| check_name | TEXT NOT NULL | registered check identifier |
| status | TEXT NOT NULL | `pass`, `fail`, `warning`, `error`, `skipped` |
| result_summary | TEXT | human-readable; shown to all roles |
| result_detail | TEXT | JSON string; compliance_manager and security_reviewer only; never auditors |
| run_at | TIMESTAMP | |
| duration_ms | INTEGER | |
| triggered_by | TEXT | `scheduler`, `manual`, `test` |
| created_task_id | FK -> tasks.id | nullable; set when failure spawns a task |

#### `check_evidence`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| check_id | FK -> control_checks.id | |
| evidence_id | FK -> evidence.id | |
| created_at | TIMESTAMP | default now() |

#### `integration_runs`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| integration_name | TEXT NOT NULL | `google_workspace`, `github`, `aws`, `okta`, `sharepoint` |
| status | TEXT NOT NULL | `success`, `partial`, `failed` |
| started_at | TIMESTAMP | |
| finished_at | TIMESTAMP | nullable |
| error_message | TEXT | nullable |
| records_synced | INTEGER | default 0 |

#### `integration_snapshots`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| run_id | FK -> integration_runs.id | |
| integration_name | TEXT NOT NULL | |
| resource_type | TEXT NOT NULL | e.g., `user`, `repo`, `iam_policy` |
| resource_id | TEXT NOT NULL | external system ID |
| data | TEXT NOT NULL | JSON string; compliance_manager and security_reviewer only; never auditors |
| captured_at | TIMESTAMP | |

#### `audit_periods`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| framework_id | FK -> frameworks.id | |
| name | TEXT NOT NULL | e.g., "FY2025 SOC 2 Type II" |
| report_type | TEXT NOT NULL | `type1`, `type2` |
| observation_start | DATE | Type II only; nullable for Type I |
| observation_end | DATE | nullable |
| point_in_time_date | DATE | Type I only; nullable for Type II |
| created_by | FK -> users.id | |
| created_at | TIMESTAMP | default now() |

#### `audits`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| period_id | FK -> audit_periods.id | |
| audit_firm | TEXT | |
| status | TEXT NOT NULL | `preparation`, `in_progress`, `fieldwork`, `review`, `completed`, `cancelled`; default 'preparation' |
| early_access_date | DATE | nullable |
| fieldwork_start | DATE | nullable |
| fieldwork_end | DATE | nullable |
| report_date | DATE | nullable |
| lead_auditor_email | TEXT | nullable |
| notes | TEXT | |
| created_by | FK -> users.id | |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `audit_controls`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| audit_id | FK -> audits.id | |
| control_id | FK -> controls.id | |
| in_scope | BOOLEAN | default true |
| auditor_notes | TEXT | nullable |

#### `audit_users` (auditor assignments)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| audit_id | FK -> audits.id | |
| user_id | FK -> users.id | must have role=auditor |
| assigned_at | TIMESTAMP | |
| assigned_by | FK -> users.id | |
| access_expires_at | TIMESTAMP | nullable; defaults to fieldwork_end + 30 days |

#### `audit_requests` (PBC requests)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| audit_id | FK -> audits.id | |
| control_id | FK -> controls.id | nullable |
| created_by | FK -> users.id | |
| assigned_to | FK -> users.id | nullable; internal assignee |
| title | TEXT NOT NULL | |
| description | TEXT | |
| request_type | TEXT | `evidence_request`, `clarification`, `population`, `sample` |
| sample_size | INTEGER | nullable |
| status | TEXT | `open`, `in_review`, `fulfilled`, `closed`, `overdue`; default 'open' |
| due_date | DATE | nullable |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `audit_request_evidence`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| request_id | FK -> audit_requests.id | |
| evidence_id | FK -> evidence.id | |
| attached_by | FK -> users.id | |
| attached_at | TIMESTAMP | default now() |

#### `audit_comments`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| audit_id | FK -> audits.id | |
| request_id | FK -> audit_requests.id | nullable |
| evidence_id | FK -> evidence.id | nullable |
| parent_id | FK -> audit_comments.id | nullable; enables threading |
| author_id | FK -> users.id | |
| body | TEXT NOT NULL | |
| is_internal | BOOLEAN | default false; true = hidden from auditors |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `audit_findings`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| audit_id | FK -> audits.id | |
| control_id | FK -> controls.id | nullable |
| finding_type | TEXT | `exception`, `observation`, `management_letter`, `deficiency` |
| severity | TEXT | `low`, `medium`, `high`, `critical` |
| title | TEXT NOT NULL | |
| description | TEXT | |
| management_response | TEXT | nullable |
| status | TEXT | `open`, `remediated`, `accepted`, `closed` |
| created_by | FK -> users.id | |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `tasks` (remediation)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| control_id | FK -> controls.id | nullable |
| check_id | FK -> control_checks.id | nullable |
| title | TEXT NOT NULL | |
| description | TEXT | |
| assigned_to | FK -> users.id | nullable |
| priority | TEXT | `low`, `medium`, `high`, `critical` |
| status | TEXT | `open`, `in_progress`, `resolved`, `wont_fix`; default 'open' |
| due_date | DATE | nullable |
| resolved_at | TIMESTAMP | nullable |
| created_by | FK -> users.id | |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `audit_log`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| actor_id | FK -> users.id | nullable; null = system action |
| action | TEXT NOT NULL | dot-namespaced, e.g., `evidence.lock` |
| resource_type | TEXT | |
| resource_id | TEXT | |
| detail | TEXT | JSON string; before/after or contextual metadata |
| ip_address | TEXT | |
| user_agent | TEXT | |
| created_at | TIMESTAMP | default now() |

**Append-only constraint:** No application code may issue `UPDATE` or `DELETE` against `audit_log`. No cascade deletes may reference this table. See Section 5.5.

#### `graph_objects` (Microsoft Graph cache)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| object_type | TEXT | `user`, `group`, `site`, `drive_item` |
| external_id | TEXT UNIQUE NOT NULL | Graph object ID |
| display_name | TEXT | |
| data | TEXT | JSON string |
| synced_at | TIMESTAMP | |

#### `graph_links`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| source_id | FK -> graph_objects.id | |
| target_id | FK -> graph_objects.id | |
| relationship | TEXT | e.g., `member_of`, `owns` |
| created_at | TIMESTAMP | default now() |

### 6.3 Readiness Snapshot Tables (New in v2.1)

These tables persist the output of the Type I and Type II engines so historical readiness reports can be retrieved without re-running the full calculation, and so audit defensibility does not depend on recalculation.

#### `readiness_snapshots`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| audit_period_id | FK -> audit_periods.id | |
| report_type | TEXT NOT NULL | `type1`, `type2` |
| calculated_at | TIMESTAMP | when the engine ran |
| calculated_by | FK -> users.id | nullable; null = scheduled recalculation |
| overall_score | NUMERIC(5,2) | 0.00-100.00 |
| controls_ready | INTEGER | count of controls at Ready / Effective |
| controls_partial | INTEGER | |
| controls_not_ready | INTEGER | |
| controls_not_applicable | INTEGER | |
| summary_json | TEXT | full engine output as JSON; authoritative record |

#### `readiness_gaps`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| snapshot_id | FK -> readiness_snapshots.id | |
| control_id | FK -> controls.id | |
| gap_type | TEXT | `missing_check`, `failed_check`, `missing_evidence`, `integration_outage`, `evidence_expired` |
| gap_start | DATE | |
| gap_end | DATE | |
| severity | TEXT | `red`, `yellow` |
| detail | TEXT | human-readable explanation |

These two tables give auditors and compliance managers a defensible, timestamped record of what the system showed at the time of each readiness calculation.

### 6.4 Evidence-to-Multiple-Controls Mapping (New in v2.3)

**Known limitation in current schema:** `evidence.control_id` is a single FK, enforcing a one-to-one relationship between an evidence item and a control. In practice, one piece of evidence often satisfies multiple controls simultaneously (e.g., an MFA screenshot satisfies CC6.1 and can support CC6.6; an access review document satisfies CC6.2, CC6.3, and CC6.6).

**Fix:** Add an `evidence_controls` junction table. The `evidence.control_id` column becomes the "primary" control for display purposes and is retained for backwards compatibility, but the readiness engines must use `evidence_controls` for coverage calculations.

#### `evidence_controls`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| evidence_id | FK -> evidence.id | |
| control_id | FK -> controls.id | |
| is_primary | BOOLEAN | true for the original control_id; false for additional mappings |
| mapped_by | FK -> users.id | who added this mapping |
| created_at | TIMESTAMP | default now() |

UNIQUE constraint on `(evidence_id, control_id)`.

Migration rule: on creation of this table, backfill one row per existing evidence row using `evidence.control_id` as the primary mapping.

The readiness engines (Phase 7) must be updated to query `evidence_controls` rather than `evidence.control_id` when evaluating evidence coverage per control.

### 6.5 Policy Management Tables (New in v2.3)

SOC 2 auditors distinguish between two categories of artifacts that the current schema conflates under "evidence":

1. **Operational evidence** - screenshots, logs, exports proving a control is operating (handled by the `evidence` table)
2. **Policy documents** - written policies the organization has adopted, approved, and reviewed on a defined cycle

Vanta ships policy templates for common SOC 2 requirements (information security policy, access control policy, incident response plan, business continuity plan, acceptable use policy, etc.). This platform must support the same concept.

#### `policies`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| framework_id | FK -> frameworks.id | |
| title | TEXT NOT NULL | e.g., "Information Security Policy" |
| description | TEXT | what this policy covers |
| policy_type | TEXT | `information_security`, `access_control`, `incident_response`, `business_continuity`, `acceptable_use`, `data_classification`, `vulnerability_management`, `change_management`, `privacy`, `vendor_management`, `custom` |
| owner_user_id | FK -> users.id | nullable |
| status | TEXT | `draft`, `in_review`, `approved`, `needs_review`, `retired`; default 'draft' |
| review_frequency_days | INTEGER | e.g., 365 for annual review |
| last_approved_at | TIMESTAMP | nullable |
| next_review_date | DATE | nullable |
| approved_by | FK -> users.id | nullable |
| sharepoint_url | TEXT | nullable |
| sharepoint_item_id | TEXT | nullable |
| local_path | TEXT | nullable; dev only |
| file_name | TEXT | nullable |
| sha256_hash | TEXT | nullable; computed at upload |
| version | TEXT | e.g., "1.2" |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `policy_controls` (many-to-many)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| policy_id | FK -> policies.id | |
| control_id | FK -> controls.id | |

UNIQUE constraint on `(policy_id, control_id)`.

#### `policy_versions`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| policy_id | FK -> policies.id | |
| version | TEXT | |
| uploaded_by | FK -> users.id | |
| sharepoint_item_id | TEXT | nullable |
| sha256_hash | TEXT | nullable |
| change_summary | TEXT | |
| created_at | TIMESTAMP | default now() |

#### `policy_consistency_flags`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| policy_id | FK -> policies.id | |
| control_id | FK -> controls.id | nullable |
| flag_type | TEXT | `control_failing`, `review_overdue`, `check_gap`, `unmapped_control_reference` |
| severity | TEXT | `warning`, `error` |
| detail | TEXT | human-readable explanation of the inconsistency |
| detected_at | TIMESTAMP | when the scheduler job found this |
| resolved_at | TIMESTAMP | nullable; set when the flag is no longer applicable |
| is_active | BOOLEAN | default true; set false when resolved |

This table is the JEC equivalent of Vanta's policy-to-program consistency check, implemented as a deterministic rule engine rather than AI inference. See Section 14.5 for the full rule set.

**Policy readiness rule:** For a SOC 2 control that requires a written policy (e.g., CC6.1 requires an access control policy), the readiness engine must check that at least one `policies` row with `status='approved'` is linked via `policy_controls` and that `next_review_date >= point_in_time_date` (Type I) or was not overdue during the observation window (Type II).

### 6.6 Access Review Tables (New in v2.3)

Vanta has a structured access review workflow where system owners are assigned reviews, given deadlines, and must approve or revoke access per account. This maps to SOC 2 controls CC6.2, CC6.3, and CC6.6.

#### `access_reviews`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT NOT NULL | e.g., "Q1 2025 GitHub Access Review" |
| system_name | TEXT NOT NULL | e.g., "GitHub", "AWS Console", "Google Workspace" |
| integration_name | TEXT | nullable; links to a provider if automated |
| reviewer_user_id | FK -> users.id | system owner responsible for the review |
| assigned_by | FK -> users.id | |
| status | TEXT | `pending`, `in_progress`, `completed`, `overdue`; default 'pending' |
| due_date | DATE | |
| completed_at | TIMESTAMP | nullable |
| period_start | DATE | review covers access as of this date |
| period_end | DATE | |
| total_accounts | INTEGER | populated when review is started |
| accounts_approved | INTEGER | default 0 |
| accounts_revoked | INTEGER | default 0 |
| accounts_pending | INTEGER | default 0 |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `access_review_accounts`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| review_id | FK -> access_reviews.id | |
| external_user_id | TEXT | ID in the external system |
| email | TEXT | |
| display_name | TEXT | |
| role_in_system | TEXT | |
| is_admin | BOOLEAN | |
| employment_status | TEXT | `active`, `terminated`, `department_changed`, `unknown` |
| risk_flag | BOOLEAN | true if terminated or department changed |
| decision | TEXT | nullable; `approved`, `revoked`, `pending` |
| decision_by | FK -> users.id | nullable |
| decision_at | TIMESTAMP | nullable |
| decision_notes | TEXT | nullable |
| remediation_task_id | FK -> tasks.id | nullable; created if decision='revoked' |

**Access review completion rule:** A review is `completed` when all accounts have a decision. APScheduler daily job sets `status='overdue'` for reviews past `due_date` with `status='in_progress'` or `'pending'`. Completed reviews auto-generate an evidence record (`source_type='system_generated'`) linked to the relevant controls.

### 6.7 Personnel Compliance Tables (New in v2.3)

Vanta tracks employee-level compliance: security training completion, background checks, device compliance, and policy acknowledgement. This is required for several SOC 2 controls (CC1.4, CC1.5 - commitment to competence and HR policies).

#### `personnel`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | FK -> users.id | nullable; links to internal user if they have an account |
| email | TEXT UNIQUE NOT NULL | |
| display_name | TEXT | |
| department | TEXT | |
| title | TEXT | |
| employment_status | TEXT | `active`, `on_leave`, `terminated`; default 'active' |
| start_date | DATE | nullable |
| termination_date | DATE | nullable |
| entra_oid | TEXT | nullable; Microsoft Entra ID for cross-referencing deprovisioning |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `personnel_requirements`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT NOT NULL | e.g., "Annual Security Awareness Training" |
| requirement_type | TEXT | `training`, `background_check`, `policy_acknowledgement`, `device_enrollment` |
| applies_to | TEXT | `all`, `engineering`, `management`, `contractors` |
| due_within_days_of_hire | INTEGER | nullable |
| recurrence_days | INTEGER | nullable; e.g., 365 for annual |
| is_active | BOOLEAN | default true |
| control_id | FK -> controls.id | nullable; the SOC 2 control this satisfies |

#### `personnel_compliance_records`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| personnel_id | FK -> personnel.id | |
| requirement_id | FK -> personnel_requirements.id | |
| status | TEXT | `pending`, `completed`, `overdue`, `waived` |
| completed_at | TIMESTAMP | nullable |
| due_date | DATE | nullable |
| evidence_url | TEXT | nullable; link to training completion certificate or document |
| notes | TEXT | nullable |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

**Personnel compliance readiness rule:** For controls that require personnel compliance evidence, the readiness engine checks that all active personnel have `completed` records for required `personnel_requirements` linked to that control within the observation window.

### 6.8 Risk Register Tables (New in v2.3)

Vanta includes a risk management module. CC9.1 (Risk Assessment) requires a formal risk register with identified risks, likelihood/impact scoring, and treatment plans. The current PRD seeds CC9.1 as a manual control with no supporting data structure.

#### `risks`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| title | TEXT NOT NULL | |
| description | TEXT | |
| category | TEXT | `operational`, `security`, `compliance`, `financial`, `reputational`, `third_party` |
| owner_user_id | FK -> users.id | nullable |
| likelihood | INTEGER | 1-5 scale |
| impact | INTEGER | 1-5 scale |
| risk_score | INTEGER | computed: likelihood x impact; 1-25 |
| inherent_risk_score | INTEGER | score before controls |
| residual_risk_score | INTEGER | score after controls |
| treatment | TEXT | `accept`, `mitigate`, `transfer`, `avoid` |
| treatment_notes | TEXT | |
| status | TEXT | `open`, `mitigated`, `accepted`, `closed` |
| review_date | DATE | nullable |
| created_by | FK -> users.id | |
| created_at | TIMESTAMP | default now() |
| updated_at | TIMESTAMP | |

#### `risk_controls` (many-to-many: risks mitigated by controls)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| risk_id | FK -> risks.id | |
| control_id | FK -> controls.id | |

#### `risk_history`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| risk_id | FK -> risks.id | |
| likelihood | INTEGER | |
| impact | INTEGER | |
| risk_score | INTEGER | |
| recorded_by | FK -> users.id | |
| recorded_at | TIMESTAMP | |
| notes | TEXT | |

**CC9.1 readiness rule:** CC9.1 moves from a pure manual stub to: at least one `risks` table review cycle completed within the observation window (evidenced by `risk_history` rows), and the risk register exported as evidence. The manual_check stub for CC9.1 is replaced with a `risk_register_check` that validates the register has been reviewed within the required period.

---

### 6.9 Initial SOC 2 Control Seed

**Important disclaimer:** The following 10 controls are an MVP starter set for initial development and internal testing. They are not sufficient for a real SOC 2 audit. A production-ready SOC 2 engagement typically maps to the full AICPA Trust Services Criteria set, which covers approximately 60 criteria across the CC, A, PI, P, and C categories. The remaining controls must be added before any actual audit engagement begins. The roadmap in Section 14 tracks this as a high-priority item.

The following 10 controls must be seeded via `scripts/seed_controls.py`. The script must be idempotent (safe to re-run without creating duplicates).

| Code | Title | Category | Automated | Frequency |
|---|---|---|---|---|
| CC6.1 | MFA Enforcement | Logical and Physical Access Controls | Yes | Continuous |
| CC6.2 | Access Provisioning | Logical and Physical Access Controls | Partial | Monthly |
| CC6.3 | Access Revocation / Deprovisioning | Logical and Physical Access Controls | Yes | Continuous |
| CC6.6 | Least Privilege / Privileged Access Review | Logical and Physical Access Controls | Partial | Quarterly |
| CC7.1 | Vulnerability Detection | System Operations | Yes | Daily |
| CC7.2 | Security Monitoring / Incident Detection | System Operations | Yes | Continuous |
| CC8.1 | Change Management | Change Management | Partial | On Change |
| CC9.1 | Risk Assessment | Risk Mitigation | No | Annual |
| A1.1 | Backup Verification | Availability | Yes | Daily |
| P1.1 | Privacy Notice | Privacy | No | Annual |

Each seeded control must populate all non-nullable columns including `framework_id`, `type1_status='not_started'`, `type2_status='not_started'`, and an `evidence_requirements` narrative string describing what evidence is needed to satisfy the control.

---

## 7. Implementation Phases

---

### Phase 1 - Foundation and Data Model

**Goal:** Clean schema, migrations, and seeds on top of the existing app. Do not break `auth.py` or any currently working route.

**Deliverables:**
- `alembic/versions/001_new_tables.py` - Alembic migration adding all new tables from Section 6 that do not already exist; uses integer PKs throughout
- `scripts/seed_controls.py` - idempotent seed for the 10 controls in Section 6.4
- `app/models/` - SQLAlchemy declarative model files for all new tables: `controls.py`, `evidence.py`, `audits.py`, `checks.py`, `tasks.py`, `graph.py`, `readiness.py`
- `app/db/session.py` - SQLAlchemy engine + session factory; `DATABASE_URL` env var switches between SQLite and PostgreSQL without code changes
- `app/core/config.py` - Pydantic `BaseSettings` loaded from environment and `.env`

**Constraints:**
- Do not modify `auth.py` or rename any existing route in this phase
- If the `users` table already exists, the migration must use `ALTER TABLE` / `ADD COLUMN` rather than `DROP TABLE`
- All new FK columns reference integer IDs
- Existing data must be migrated forward where possible; destructive schema resets (DROP TABLE, DROP COLUMN on tables with live data) require explicit written approval from the project owner before execution

**Acceptance criteria:**
- `alembic upgrade head` completes without error on a clean SQLite database
- `alembic upgrade head` completes without error on a clean PostgreSQL 16 database
- `python scripts/seed_controls.py` run twice produces exactly 10 controls
- All foreign keys resolve; `alembic downgrade` reverses the migration cleanly
- The existing app starts normally after migration; no existing routes return 500

---

### Phase 2 - Check Engine

**Goal:** Automated control checks that run on schedule, write results, update readiness state, and create remediation tasks on failure.

**Architecture:**

```
app/services/checks/
  base.py          BaseCheck abstract class; CheckResult dataclass
  registry.py      CheckRegistry singleton; checks register by control_code
  runner.py        CheckRunner - executes a check, writes control_checks row,
                   optionally writes evidence row, creates tasks row on failure
  scheduler.py     APScheduler wiring inside FastAPI lifespan event
  modules/
    mfa_check.py
    access_provisioning_check.py
    deprovisioning_check.py
    privileged_access_check.py
    vulnerability_check.py
    security_monitoring_check.py
    change_management_check.py
    backup_check.py
    manual_check.py
```

**Check modules and data sources:**

| Module | Controls | Primary Data Source |
|---|---|---|
| `mfa_check.py` | CC6.1 | Google Workspace Admin SDK |
| `access_provisioning_check.py` | CC6.2 | Google Workspace / Okta |
| `deprovisioning_check.py` | CC6.3 | Google Workspace / Okta |
| `privileged_access_check.py` | CC6.6 | Google Workspace Admin + AWS IAM |
| `vulnerability_check.py` | CC7.1 | GitHub Dependabot alerts / AWS Inspector |
| `security_monitoring_check.py` | CC7.2 | AWS CloudWatch alarm states |
| `change_management_check.py` | CC8.1 | GitHub branch protection rules |
| `backup_check.py` | A1.1 | AWS Backup job history / S3 |
| `manual_check.py` | CC9.1, P1.1 | Stub - returns `skipped` with guidance message |

**Rules:**
- No random or simulated results in any production code path
- `TEST_MODE=true` environment variable activates deterministic fixture responses for every check module - required in development and all automated tests
- Every check execution writes a `control_checks` row regardless of outcome
- A `pass` result flags the control for Type I/II engine re-evaluation (does not directly update readiness scores - that is the engine's job)
- A `fail` or `error` result immediately sets `controls.type2_status='failing'` and creates a `tasks` row if no open task already exists for that control from the same check name
- `result_detail` (raw integration data) must never be surfaced to auditors; `result_summary` (human-readable sentence) is safe for all roles

---

### Phase 3 - Integrations

**Goal:** Provider connectors that pull source data, normalize into snapshots, and log every run without blocking the API.

**Location:** `app/services/integrations/`

**Base contract:**
```python
class IntegrationBase:
    name: str
    def health_check(self) -> bool: ...
    def sync(self) -> IntegrationRunResult: ...
```

Each `sync()` must:
1. Write an `integration_runs` row at start with `status='in_progress'`
2. Pull data from the external API
3. Write normalized `integration_snapshots` rows
4. Update the `integration_runs` row to `success`, `partial`, or `failed` on completion
5. Never raise an unhandled exception - catch all errors, log, update the run row, and return a failed result

**Required providers:**

#### SharePoint / Microsoft Graph (`sharepoint.py`)
Auth: MSAL client credentials (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)

Operations:
- `upload_file(control_code, filename, content_bytes) -> SharePointUploadResult` - uploads to `/JEC-Compliance/Evidence/{control_code}/`; creates folder if absent
- `download_file(item_id) -> bytes`
- `get_file_metadata(item_id) -> dict`
- `copy_to_locked_folder(item_id, audit_id, evidence_id) -> str` - copies to `/JEC-Compliance/Evidence/Locked/{audit_id}/{evidence_id}/`
- `get_download_url(item_id) -> str` - returns a short-lived download URL or proxies the download according to tenant policy; do not assume `createLink` sharing links are permitted in all tenant configurations; consult tenant SharePoint settings before choosing the method

Evidence file handling:
- SHA-256 hash is computed locally before upload and stored in `evidence.sha256_hash`
- On lock: re-download bytes from SharePoint, recompute SHA-256, compare to stored hash; reject lock if mismatch
- Locked copies stored in locked folder; `sharepoint_url` and `sharepoint_item_id` updated to the locked copy on success

#### Google Workspace (`google_workspace.py`)
Auth: Service account with domain-wide delegation; key file path via `GOOGLE_SERVICE_ACCOUNT_JSON`

Pulls: admin users, MFA enrollment status per user, suspended/active status, admin role assignments

Normalizes into `integration_snapshots` with `resource_type='user'`

#### GitHub (`github.py`)
Auth: GitHub App or PAT; `GITHUB_TOKEN` and `GITHUB_ORG`

Pulls: repositories, branch protection rules (require PR review, require status checks, dismiss stale reviews, restrict pushes), Dependabot alert counts by severity

Normalizes into `integration_snapshots` with `resource_type='repo'` and `resource_type='vulnerability_alert'`

#### AWS (`aws.py`)
Auth: STS AssumeRole via `AWS_ROLE_ARN`; read-only policy required

Pulls: IAM users with admin-level policies, CloudWatch alarm states, AWS Backup recent job results, S3 bucket encryption configuration

Normalizes into `integration_snapshots`

#### Okta (`okta.py`) - conditional
Enabled only when both `OKTA_DOMAIN` and `OKTA_API_TOKEN` are present in the environment

Pulls: users, lifecycle status, app assignments, recent deprovisioning events

**Data access rules:**
- `integration_snapshots.data` readable by `compliance_manager` and `security_reviewer` only
- Auditors receive zero snapshot data under any circumstances
- `control_checks.result_detail` follows the same restriction

---

### Phase 3b - Policy Management

**Goal:** Give compliance managers a place to store, version, approve, and review written policies as artifacts distinct from operational evidence.

**New pages:** `/policies` (list), `/policies/{id}` (detail + version history + linked controls)

**Key endpoints:**
- `GET /api/v1/policies` - list all policies with status and next review date
- `POST /api/v1/policies` - create policy (upload file or draft in-platform)
- `PATCH /api/v1/policies/{id}/approve` - Compliance Manager approves; sets `status='approved'`, `last_approved_at`
- `POST /api/v1/policies/{id}/version` - upload a new version
- `GET /api/v1/policies/{id}/controls` - list controls this policy satisfies
- `POST /api/v1/policies/{id}/controls` - link policy to additional controls

**APScheduler job:** daily scan for policies where `next_review_date < today + 30 days`; set `status='needs_review'` and surface on dashboard.

**Readiness engine update:** Phase 7 engines must include policy coverage as a readiness signal for controls that have a `policy_controls` mapping. A control requiring a policy is not Ready unless an approved, non-overdue policy is linked.

---

### Phase 3c - Access Reviews

**Goal:** Structured quarterly/annual access reviews for each integrated system, with per-account approve/revoke decisions and automatic evidence generation.

**New page:** `/access-reviews` (list + detail)

**Key endpoints:**
- `GET /api/v1/access-reviews` - list reviews
- `POST /api/v1/access-reviews` - create review (system, reviewer, due date, period)
- `POST /api/v1/access-reviews/{id}/start` - populate `access_review_accounts` from latest integration snapshot for the system
- `PATCH /api/v1/access-reviews/{id}/accounts/{account_id}` - record approve/revoke decision
- `POST /api/v1/access-reviews/{id}/complete` - mark complete; auto-generate evidence record

**Risk flagging:** on `start`, flag accounts where the personnel record shows `employment_status='terminated'` or `department_changed` - these appear at the top of the review list with a visual warning, matching Vanta's automatic flagging behavior.

**Remediation:** a `revoked` decision creates a `tasks` row assigned to the system owner to remove access, with a due date of 5 business days.

**Evidence auto-generation:** on completion, create an `evidence` row with `source_type='system_generated'`, `status='submitted'`, linked to CC6.2, CC6.3, and CC6.6 via `evidence_controls`.

---

### Phase 3d - Personnel Compliance

**Goal:** Track whether all active employees have completed required security training, background checks, and policy acknowledgements.

**New page:** `/personnel` (compliance manager view of all staff); `/my-compliance` (employee self-service view)

**Key endpoints:**
- `GET /api/v1/personnel` - list all personnel with compliance status summary
- `GET /api/v1/personnel/{id}` - individual compliance record
- `PATCH /api/v1/personnel/{id}/requirements/{req_id}` - mark completed, upload certificate
- `GET /api/v1/personnel/requirements` - list all active requirements
- `POST /api/v1/personnel/requirements` - create new requirement

**Sync from integration:** the Google Workspace provider populates `personnel` from the directory sync; `employment_status` is updated when a user is suspended or deleted in Google Workspace.

**APScheduler job:** daily scan sets `personnel_compliance_records.status='overdue'` for records past `due_date`. Dashboard widget shows count of employees with overdue compliance items.

**Evidence auto-generation:** when all active personnel complete a requirement, auto-generate an evidence record for the linked control.

---

### Phase 3e - Risk Register

**Goal:** Formal risk register satisfying CC9.1, with likelihood/impact scoring, treatment plans, and reviewable history.

**New page:** `/risk-register`

**Key endpoints:**
- `GET /api/v1/risks` - list risks with current scores
- `POST /api/v1/risks` - create risk
- `PATCH /api/v1/risks/{id}` - update risk (scores, treatment, status)
- `POST /api/v1/risks/{id}/review` - record a review cycle (writes `risk_history` row)
- `GET /api/v1/risks/{id}/history` - score history over time
- `POST /api/v1/risks/export` - export risk register as PDF or CSV for audit evidence

**CC9.1 check update:** replace the manual stub with `risk_register_check` that passes if at least one `risk_history` row exists within the required review period and at least 3 risks are documented.

---

### Phase 4 - Evidence Pipeline

**Goal:** Complete evidence lifecycle from upload through lock and inclusion in an audit export.

#### Manual Upload
`POST /api/v1/evidence/upload` - multipart/form-data

Required fields: `control_id`, `title`, `valid_from`, file upload  
Optional fields: `description`, `valid_to`

Processing:
1. Validate file extension against allowlist: `pdf`, `docx`, `xlsx`, `png`, `jpg`, `jpeg`, `txt`, `csv`, `zip`
2. Validate MIME type server-side using `python-magic` (do not trust client-supplied `Content-Type`)
3. Enforce 50 MB file size limit
4. Compute SHA-256 of file bytes
5. Upload to SharePoint via `sharepoint.upload_file()` (or local path in dev mode)
6. Create `evidence` row with `status='submitted'`
7. Write `audit_log` entry for `evidence.upload`

#### Evidence Review
- `PATCH /api/v1/evidence/{id}/accept` - Compliance Manager or Security Reviewer; sets `status='accepted'`, `reviewed_by`
- `PATCH /api/v1/evidence/{id}/reject` - requires `rejection_reason` in body; sets `status='rejected'`
- `PATCH /api/v1/evidence/{id}/flag` - sets `status='flagged'` with optional note

#### Evidence Locking
`PATCH /api/v1/evidence/{id}/lock` - Compliance Manager only

Pre-lock validation sequence:
1. Current `status` must be `'accepted'`; any other status returns 422
2. Re-download file bytes from SharePoint
3. Recompute SHA-256; compare to `evidence.sha256_hash`; mismatch returns 422 with explanation
4. Call `sharepoint.copy_to_locked_folder()`; update `sharepoint_item_id` and `sharepoint_url` to locked copy
5. Set `status='locked'`, `locked_at=now()`, `locked_by=current_user.id`
6. Write `audit_log` entry for `evidence.lock`

Once locked: the evidence row is immutable. No edits, re-uploads, status changes, or deletes are permitted by any application code.

#### Evidence Expiry (APScheduler daily job)
Scans all evidence where `status NOT IN ('locked', 'expired')` and `valid_to IS NOT NULL`:
- If `valid_to` is within 30 days from today -> set `status='stale'`
- If `valid_to` is before today -> set `status='expired'`

Locked evidence is never expired regardless of `valid_to`.

#### Evidence Statuses

| Status | Description |
|---|---|
| submitted | Uploaded; awaiting review |
| accepted | Approved by reviewer; eligible for locking |
| rejected | Rejected; `rejection_reason` populated |
| locked | Locked, hash-verified, immutable; included in export |
| stale | Within 30 days of `valid_to`; needs renewal |
| expired | Past `valid_to`; no longer valid for new audit coverage |
| flagged | Needs attention from internal team or auditor |
| not_applicable | Explicitly marked N/A for this control |

---

### Phase 5 - Audit Workflow

**Goal:** Full Vanta-style audit engagement management.

#### Audit Period Creation
`POST /api/v1/audit-periods` - Compliance Manager only

For Type I: supply `point_in_time_date`  
For Type II: supply `observation_start` and `observation_end`  
Both require `framework_id`, `name`, `report_type`

#### Audit Engagement Creation
`POST /api/v1/audits`

Fields: `period_id`, `audit_firm`, `early_access_date` (optional), `fieldwork_start`, `fieldwork_end`, `notes`

On creation: all controls in the framework are inserted into `audit_controls` with `in_scope=true`. Compliance Manager may then remove out-of-scope controls via `PATCH /api/v1/audits/{id}/controls/{control_id}`.

#### Auditor Assignment
`POST /api/v1/audits/{id}/auditors`

- Target user must have `role='auditor'`; 422 if not
- Sets `access_expires_at = fieldwork_end + 30 days` unless overridden in request body
- If the auditor does not yet have a `scoped_token`, one is generated and stored on the `users` row at assignment time
- Updates `users.token_expires_at` to match the assignment expiry used for token authentication
- The portal link displayed in the audit detail UI is constructed from `scoped_token` as `/?token={scoped_token}#auditor-portal`; scope is always enforced server-side, not encoded in the link
- Auditor gains scoped portal access immediately upon assignment
- Writes `audit_log` entry with `action='auditor.assigned'`

#### Auditor Listing
`GET /api/v1/auditors` - Compliance Manager only
Returns all users with `role='auditor'` and `is_active=true`. Used to populate the assignment form dropdown in the audit detail UI.

`GET /api/v1/audits/{id}/auditors` - Compliance Manager only
Returns all `audit_users` rows for the audit, including `access_expires_at`, assignment date, `scoped_token`, and `token_expires_at`.

#### Auditor Revocation
`DELETE /api/v1/audits/{id}/auditors/{user_id}`

- Returns 404 if the `audit_users` row does not exist (auditor was never assigned or already revoked)
- Deletes the `audit_users` row; does not invalidate the user's `scoped_token` (see Section 5.7)
- Writes `audit_log` entry with `action='auditor.revoked'`
- If the auditor has no remaining `audit_users` rows across any audit, they retain their token but all scope checks return 403

#### Audit Lifecycle Transitions

```
preparation -> in_progress -> fieldwork -> review -> completed
                                              ->
                                          cancelled
```

All transitions driven by Compliance Manager via `PATCH /api/v1/audits/{id}`.  
`completed` status sets `audit_users.access_expires_at = now()` for all assigned auditors.

#### Auditor Scope Enforcement (Middleware / Dependency)

Every API request from an auditor passes two checks:
1. `require_role('auditor')` - active session with auditor role
2. `require_audit_scope(audit_id)` - resource belongs to the auditor's assigned engagement and is within the audit window

Auditors may read:
- Controls in `audit_controls` where `in_scope=true` for their audit
- Evidence where `control_id` is in scope AND (`valid_from` falls within observation window OR evidence is attached to a request in their audit)
- `audit_requests` for their audit
- `audit_comments` where `is_internal=false`
- `audit_findings` for their audit
- `control_checks.result_summary` only (never `result_detail`)

Auditors may never read:
- `integration_snapshots.data`
- `control_checks.result_detail`
- Evidence outside the audit window unless attached to a request
- Internal comments (`is_internal=true`)
- Any other audit engagement
- User management data

#### "View as Auditor" Preview
`GET /api/v1/audits/{id}/preview-as-auditor` - Compliance Manager only  
Returns the identical payload shape the auditor portal returns. Does not require an auditor account.

#### Audit Export
`POST /api/v1/audits/{id}/export` - Compliance Manager only

Generates a ZIP archive (streamed; not stored server-side):

```
export_{audit_id}_{timestamp}.zip
  manifest.json                      audit metadata, control list, evidence inventory with hashes
  controls/
    {control_code}.json              status, description, narratives, check history summary
  evidence/
    {evidence_id}/
      {original_filename}            file from locked SharePoint folder
      metadata.json                  evidence row data + hash
  findings/
    findings.json
  requests/
    {request_id}.json                PBC thread export
  readiness/
    type1_snapshot.json              if applicable
    type2_snapshot.json              including gap timeline; if applicable
  audit_log.json                     audit-relevant events only
```

Rules:
- Only `status='locked'` evidence files are included as files
- `status='accepted'` evidence is listed in manifest with note: "Accepted but not locked - file excluded from package"
- Every export writes an `audit_log` entry with `action='export.generated'`

---

### Phase 6 - PBC / Custom Evidence Requests

**Goal:** Structured request-response workflow between auditors and the internal compliance team.

#### Auditor Creates Request
`POST /api/v1/audits/{audit_id}/requests`  
Available to: Auditor (for their assigned audit), Compliance Manager

Fields: `title`, `description`, `control_id` (optional), `request_type`, `sample_size` (optional), `due_date`

#### Internal Team Responds
- `PATCH /api/v1/requests/{id}/assign` - Compliance Manager assigns to internal user
- `POST /api/v1/requests/{id}/evidence` - attach existing evidence by `evidence_id` or upload new file
- `PATCH /api/v1/requests/{id}/close` - mark fulfilled or closed

#### Auditor Updates Status
`PATCH /api/v1/requests/{id}/status`  
Auditor may set: `accepted`, `flagged`, `not_applicable`

#### Comments (Threaded)
`POST /api/v1/requests/{id}/comments`

Fields: `body`, `is_internal` (Compliance Manager and Security Reviewer only), `parent_id` (for threading)

- `is_internal=true` comments are stripped from all auditor-facing API responses
- Every comment writes an `audit_log` entry with `action='request.comment'`

#### Overdue Tracking
APScheduler daily job: requests where `due_date < today AND status='open'` -> set `status='overdue'`  
Dashboard surfaces overdue count with a visual alert.

---

### Phase 7 - Type I and Type II Readiness Engines

**Goal:** Real, calculated readiness that is persisted, timestamped, and audit-defensible. Not a dashboard flag.

---

#### Type I Readiness Engine

**Input:** `audit_period` with `report_type='type1'` and a `point_in_time_date` (PIT)

**Algorithm - per in-scope control:**

1. **Check coverage:** Find the most recent `control_checks` row with `run_at <= PIT` and `control_id` matching. Skip check requirement for manual controls (`is_automated=false`).
2. **Evidence coverage:** Find at least one `evidence` row where:
   - `status IN ('accepted', 'locked')`
   - `valid_from <= PIT`
   - `valid_to IS NULL OR valid_to >= PIT`
3. **Readiness decision:**
   - `Ready` - check status is `pass` (or manual control) AND evidence coverage met
   - `Partial` - evidence exists but check is `warning`, or check passes but evidence is `stale`
   - `Not Ready` - no check run on or before PIT, or check is `fail`/`error`, or no valid evidence
   - `Not Applicable` - control has `type1_status='not_applicable'`

**Output:**
- Per-control readiness status and reason string
- `overall_score = ready_count / in_scope_count x 100`
- Written to `readiness_snapshots` and per-control gaps to `readiness_gaps`
- Returned as JSON via `GET /api/v1/audits/{id}/readiness/type1`

---

#### Type II Readiness Engine

**Input:** `audit_period` with `report_type='type2'`, `observation_start` (OS), `observation_end` (OE)

**Algorithm - per in-scope control:**

1. **Check continuity analysis:**
   - Retrieve all `control_checks` rows where `run_at BETWEEN OS AND OE` for the control
   - Compute expected check frequency in days from `controls.frequency`
   - Identify gaps: any interval between consecutive checks exceeding `2 x frequency_days`
   - Identify outage periods: any single gap exceeding 7 days (hard threshold)

2. **Failure rate analysis:**
   - Count checks with `status IN ('fail', 'error')` vs total checks in window
   - Flag if failure rate exceeds 10% of total checks
   - Flag if any single continuous failure period exceeds 7 consecutive days

3. **Evidence continuity analysis:**
   - Divide the observation window into calendar months
   - For each month: at least one `evidence` row must satisfy `status IN ('accepted', 'locked')` AND `valid_from <= last_day_of_month` AND `(valid_to IS NULL OR valid_to >= first_day_of_month)`
   - Write one `readiness_gaps` row per month with no qualifying evidence

4. **Integration dependency analysis:**
   - For automated controls: check `integration_runs` for the required integration provider
   - Flag any gap where no `status='success'` run occurred for more than `2 x expected_sync_frequency`

5. **Gap timeline construction:**
   Produce a chronological list of period segments for the control, each with:
   - `start_date`, `end_date`
   - `color`: `green` (passing checks + evidence present), `yellow` (warnings or stale evidence), `red` (failing checks or missing evidence)
   - `reason`: human-readable explanation

**Effectiveness decision (per control):**
- `Operationally Effective` - no red periods; yellow periods total less than 5% of window; all required integrations had successful runs
- `Partially Effective` - yellow periods present but no extended red periods
- `Not Effective` - any red period exists, failure rate exceeded threshold, or evidence gap month found

**Output:**
- Per-control effectiveness assessment with full gap timeline array
- `overall_score = effective_count / in_scope_count x 100`
- Written to `readiness_snapshots` and per-gap rows to `readiness_gaps`
- Gap timeline included in `summary_json` on the snapshot row
- Returned via `GET /api/v1/audits/{id}/readiness/type2`
- Included in audit export ZIP as `readiness/type2_snapshot.json`

**Type II is never a single boolean.** The gap timeline is the primary artifact.

---

### Phase 8 - Dashboard and Frontend

**Technology:** Static HTML + CSS + Vanilla JavaScript served via FastAPI `StaticFiles`. No framework migration unless the team explicitly decides later.

#### Pages

| Page | URL Path | Accessible By |
|---|---|---|
| Login | `/login` | Public |
| Home / Dashboard | `/` | All internal roles |
| Controls Inventory | `/controls` | All internal |
| Control Detail | `/controls/{id}` | All internal |
| Evidence Locker | `/evidence` | All internal |
| Evidence Upload | `/evidence/upload` | Control Owner, Compliance Manager |
| Evidence Detail | `/evidence/{id}` | All internal |
| Integrations | `/integrations` | Compliance Manager, Security Reviewer |
| My Work / Tasks | `/tasks` | All internal |
| Audits Overview | `/audits` | Compliance Manager, Security Reviewer |
| Audit Detail | `/audits/{id}` | Compliance Manager, Security Reviewer |
| Auditor Portal | `/auditor-portal` | Auditor only |
| PBC Requests | `/requests` | Compliance Manager, Auditor |
| Reports / Exports | `/reports` | Compliance Manager |
| Settings / RBAC | `/settings` | Compliance Manager |
| Audit Log Viewer | `/audit-log` | Compliance Manager |
| Policies | `/policies` | All internal |
| Policy Detail | `/policies/{id}` | All internal |
| Access Reviews | `/access-reviews` | Compliance Manager, Security Reviewer |
| Personnel Compliance | `/personnel` | Compliance Manager |
| My Compliance | `/my-compliance` | All internal (self-service) |
| Risk Register | `/risk-register` | Compliance Manager, Security Reviewer |

#### Dashboard Widgets (Home)

- SOC 2 overall readiness score (%)
- Type I readiness score (most recent Type I snapshot)
- Type II readiness score (current observation window snapshot)
- Control status breakdown: passing / failing / missing evidence (count + bar)
- Open remediation tasks by priority (critical / high / medium / low)
- Open PBC requests: total open + overdue count in red
- Active audit engagements: name, firm, status, days remaining in fieldwork
- Integration health: one indicator per provider (green = last sync successful; yellow = last sync partial; red = last sync failed or no sync in 24 h)
- Evidence expiring within 30 days: list with control name and days remaining
- Recent audit log: last 10 entries with actor, action, timestamp
- Personnel compliance: count of employees with overdue requirements
- Policies needing review: count of policies where `next_review_date < today + 30 days`
- Open access reviews: count pending + count overdue
- Risk register summary: count of open risks by score band (critical 20-25, high 15-19, medium 8-14, low 1-7)

#### Frontend Architecture Notes

- All API calls use `fetch()` with `credentials: 'include'` (session cookie)
- CSRF token injected per page via `<meta name="csrf-token" content="...">` and sent as `X-CSRF-Token` header on all mutating requests
- Current user role is injected as `window.__JEC_USER__ = { id, email, displayName, role }` on page load; frontend uses this for conditional rendering only - server enforces all permissions regardless
- No inline scripts; all JavaScript in `/static/js/`
- Chart.js is acceptable for dashboard charts; no other heavy JS frameworks
- Frontend pages call `/api/v1/` routes as pages are rebuilt; old direct routes remain as aliases until replaced

---

### Phase 9 - Security and Hardening

#### Authentication
- MSAL redirect flow for all users; no password auth
- Session stored in a signed, `httponly=True`, `samesite='strict'`, `secure=True` (production only) cookie
- Session TTL: 8 hours; auditor sessions additionally expire at `access_expires_at`

#### RBAC Enforcement
- FastAPI dependency `require_role(*roles)` applied to every protected route
- Auditor scope check is a separate dependency `require_audit_scope(audit_id)` composed on top of `require_role('auditor')`
- Role is read from the database on every request; it is not trusted from the session token alone

#### CSRF
- All state-changing endpoints (POST, PATCH, PUT, DELETE) require `X-CSRF-Token` header matching the session-bound token
- GET and HEAD endpoints are read-only and exempt
- CSRF token regenerated on login

#### Input Validation
- All request bodies validated by Pydantic v2 models
- File upload: MIME type validated server-side with `python-magic`; client-supplied `Content-Type` is ignored
- File names: `evidence.file_name` stores the display name only; all SharePoint and local paths use internal UUID-based or control-code-based names; no user input interpolated into file paths

#### Rate Limiting
- Auditor-facing routes: 60 requests/minute per session
- Evidence download: 20 requests/minute per user
- Login: 10 attempts per IP per 15 minutes
- Implement with `slowapi` or equivalent FastAPI-compatible middleware

#### Secrets Management
- All secrets via environment variables; `.env` in `.gitignore`; `.env.example` committed with placeholder values
- Required: `DATABASE_URL`, `SECRET_KEY`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`, `SHAREPOINT_SITE_URL`, `SHAREPOINT_DRIVE_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GITHUB_TOKEN`, `GITHUB_ORG`, `AWS_ROLE_ARN`, `AWS_REGION`, `REDIS_URL`
- Optional: `OKTA_DOMAIN`, `OKTA_API_TOKEN`

#### Audit Log Events (Required)

Every listed action must produce an `audit_log` row within the same request/transaction:

| Category | Actions |
|---|---|
| Auth | `user.login`, `user.logout`, `session.expired` |
| Evidence | `evidence.upload`, `evidence.accept`, `evidence.reject`, `evidence.flag`, `evidence.lock`, `evidence.download`, `evidence.delete_attempt` |
| Checks | `check.run`, `check.fail`, `task.created_from_check` |
| Audits | `audit.create`, `audit.status_change`, `auditor.assigned`, `auditor.access_expired` |
| Requests | `request.create`, `request.status_change`, `request.comment` |
| Export | `export.generated` |
| Controls | `control.status_change`, `control.owner_change` |
| Integrations | `integration.sync_start`, `integration.sync_complete`, `integration.sync_failed` |
| Admin | `user.role_change`, `user.deactivated` |

Append-only: no `UPDATE` or `DELETE` on `audit_log` anywhere in application code (see Section 5.5).

#### SharePoint Security
- Download URLs are short-lived and obtained according to tenant policy (see Section 7, SharePoint provider notes)
- Files are not served through the FastAPI process in production; in dev mode only, small files may be proxied for convenience
- All SharePoint paths use UUID-based or control-code-based names; user-supplied filenames are never interpolated into paths

---

### Phase 10 - Testing

**Framework:** pytest + FastAPI `TestClient`

#### Test File Structure

```
tests/
  conftest.py                   fixtures: in-memory SQLite DB, TestClient,
                                mock authenticated users for each role
  unit/
    test_check_engine.py        CheckRegistry, CheckRunner, task creation logic
    test_readiness_type1.py     Type I algorithm with known state fixtures
    test_readiness_type2.py     Type II gap detection with injected check history
    test_evidence_hash.py       hash computation, lock acceptance, lock rejection on mismatch
    test_rbac.py                each role against permitted and forbidden routes
  integration/
    test_auth.py                login redirect, session cookie, role injection
    test_evidence_pipeline.py   upload -> accept -> lock full flow; SharePoint stubbed
    test_audit_workflow.py      period -> audit -> auditor assign -> status transitions
    test_pbc_requests.py        create -> assign -> attach evidence -> comment -> close
    test_export.py              ZIP structure, manifest correctness, only locked files included
    test_auditor_scope.py       out-of-scope access -> 403; snapshot access -> 403;
                                internal comment -> absent from response;
                                access expiry enforced
```

#### Required Test Coverage

| Area | What to Assert |
|---|---|
| Schema | `alembic upgrade head` succeeds on clean SQLite and PostgreSQL; all tables created; FK constraints enforced |
| Seed | `seed_controls.py` run twice -> exactly 10 controls with correct codes and statuses |
| Auth | Unauthenticated request -> 401; authenticated -> 200; role injected into session |
| RBAC | Viewer cannot POST evidence; Auditor cannot access `/settings`; Control Owner cannot lock |
| Auditor scope | Out-of-scope control -> 403; `result_detail` absent from check response; internal comment absent; snapshot data -> 403 |
| Evidence upload | File accepted; hash stored; SharePoint stub called; `audit_log` row written |
| Evidence hash | Lock with correct hash -> 200 and `status='locked'`; lock with tampered hash -> 422 |
| Evidence locking | Locked evidence: PATCH -> 422; delete attempt -> 422 |
| Audit creation | Period and audit created; all framework controls added to `audit_controls` |
| Auditor assignment | Wrong-role user -> 422; `access_expires_at` computed correctly; missing `scoped_token` generated; existing token reused; `token_expires_at` updated |
| Auditor revocation | Missing assignment -> 404; valid revocation -> 204; `auditor.revoked` audit log row written; revoked audit access -> 403 |
| PBC request | Full create -> assign -> attach -> comment thread -> close flow |
| PBC overdue scan | Past-due open request -> `status='overdue'`; fulfilled/closed requests unchanged; `request.overdue` audit log row written |
| Export | ZIP contains manifest; locked evidence file present; accepted-but-unlocked evidence listed but file absent |
| Check engine (TEST_MODE) | Deterministic fixture returned; `control_checks` row written; task created on injected fail |
| Integration failure | Provider raises exception -> `integration_runs.status='failed'`; health endpoint reflects failure; no unhandled 500 |
| Type I | Known pass+evidence -> `Ready`; known fail -> `Not Ready`; known partial state -> `Partial`; snapshot written |
| Type II gap | Injected 10-day check gap -> `readiness_gaps` row with `color='red'`; injected missing-evidence month -> flagged |
| Export readiness snapshots | Audit export ZIP contains `readiness/type1_snapshot.json` and `readiness/type2_snapshot.json` |

#### Test Mode
- `TEST_MODE=true` activates fixture responses for all check modules (no live API calls)
- Integration providers are mocked via `pytest-mock` or FastAPI dependency overrides in `conftest.py`
- SharePoint operations use a local filesystem stub

---

## 8. API Surface Summary

All new routes under `/api/v1/`. Existing routes outside this prefix are preserved as compatibility aliases until the frontend is updated. FastAPI auto-generates OpenAPI at `/docs` and `/redoc`.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Service health + integration status |
| GET | `/api/v1/dashboard` | Dashboard summary payload |
| GET | `/api/v1/controls` | List controls with readiness state |
| GET | `/api/v1/controls/{id}` | Control detail + recent checks + evidence |
| PATCH | `/api/v1/controls/{id}` | Update owner, status |
| GET | `/api/v1/evidence` | List evidence (filterable by control, status, date) |
| POST | `/api/v1/evidence/upload` | Upload new evidence |
| GET | `/api/v1/evidence/{id}` | Evidence detail |
| PATCH | `/api/v1/evidence/{id}/accept` | Accept evidence |
| PATCH | `/api/v1/evidence/{id}/reject` | Reject with reason |
| PATCH | `/api/v1/evidence/{id}/flag` | Flag evidence |
| PATCH | `/api/v1/evidence/{id}/lock` | Lock (hash verify + SharePoint copy) |
| GET | `/api/v1/evidence/{id}/download` | Download URL or proxied file |
| GET | `/api/v1/checks` | Recent check history |
| POST | `/api/v1/checks/run/{control_code}` | Trigger manual check run |
| GET | `/api/v1/integrations` | Integration status summary |
| POST | `/api/v1/integrations/{name}/sync` | Trigger manual sync |
| GET | `/api/v1/audit-periods` | List audit periods |
| POST | `/api/v1/audit-periods` | Create audit period |
| GET | `/api/v1/audits` | List audit engagements |
| POST | `/api/v1/audits` | Create audit engagement |
| GET | `/api/v1/audits/{id}` | Audit detail |
| PATCH | `/api/v1/audits/{id}` | Update audit (status, dates, notes) |
| PATCH | `/api/v1/audits/{id}/controls/{control_id}` | Update in-scope flag or auditor notes |
| GET | `/api/v1/auditors` | List eligible auditors (role=auditor, is_active=true) |
| POST | `/api/v1/audits/{id}/auditors` | Assign auditor; generates scoped_token if absent |
| GET | `/api/v1/audits/{id}/auditors` | List assigned auditors with access details |
| DELETE | `/api/v1/audits/{id}/auditors/{user_id}` | Revoke auditor; 404 if not assigned; logs auditor.revoked |
| GET | `/api/v1/audits/{id}/preview-as-auditor` | Preview auditor view (Compliance Manager only) |
| POST | `/api/v1/audits/{id}/export` | Generate and stream export ZIP |
| GET | `/api/v1/audits/{id}/readiness/type1` | Type I readiness report |
| GET | `/api/v1/audits/{id}/readiness/type2` | Type II readiness report with gap timeline |
| GET | `/api/v1/audits/{id}/requests` | List PBC requests for audit |
| POST | `/api/v1/audits/{id}/requests` | Create PBC request |
| GET | `/api/v1/requests/{id}` | Request detail + comment thread |
| PATCH | `/api/v1/requests/{id}` | Update status, assignment |
| POST | `/api/v1/requests/{id}/evidence` | Attach evidence to request |
| POST | `/api/v1/requests/{id}/comments` | Add comment |
| GET | `/api/v1/tasks` | List remediation tasks |
| PATCH | `/api/v1/tasks/{id}` | Update task |
| GET | `/api/v1/audit-log` | Query audit log (filterable by actor, action, date) |
| GET | `/api/v1/users` | List users |
| POST | `/api/v1/users` | Create / invite user |
| PATCH | `/api/v1/users/{id}` | Update role or active status |
| GET | `/api/v1/evidence/{id}/controls` | List all controls this evidence satisfies |
| POST | `/api/v1/evidence/{id}/controls` | Map evidence to an additional control |
| DELETE | `/api/v1/evidence/{id}/controls/{control_id}` | Remove a control mapping |
| GET | `/api/v1/policies` | List policies |
| POST | `/api/v1/policies` | Create policy |
| GET | `/api/v1/policies/{id}` | Policy detail |
| PATCH | `/api/v1/policies/{id}` | Update policy |
| PATCH | `/api/v1/policies/{id}/approve` | Approve policy |
| POST | `/api/v1/policies/{id}/version` | Upload new version |
| GET | `/api/v1/policies/{id}/controls` | List linked controls |
| POST | `/api/v1/policies/{id}/controls` | Link policy to control |
| GET | `/api/v1/access-reviews` | List access reviews |
| POST | `/api/v1/access-reviews` | Create access review |
| POST | `/api/v1/access-reviews/{id}/start` | Populate accounts from snapshot |
| PATCH | `/api/v1/access-reviews/{id}/accounts/{account_id}` | Record decision |
| POST | `/api/v1/access-reviews/{id}/complete` | Complete review + generate evidence |
| GET | `/api/v1/personnel` | List personnel with compliance status |
| GET | `/api/v1/personnel/{id}` | Individual compliance record |
| PATCH | `/api/v1/personnel/{id}/requirements/{req_id}` | Mark requirement complete |
| GET | `/api/v1/personnel/requirements` | List active requirements |
| POST | `/api/v1/personnel/requirements` | Create requirement |
| GET | `/api/v1/risks` | List risks |
| POST | `/api/v1/risks` | Create risk |
| PATCH | `/api/v1/risks/{id}` | Update risk |
| POST | `/api/v1/risks/{id}/review` | Record review cycle |
| GET | `/api/v1/risks/{id}/history` | Score history |
| POST | `/api/v1/risks/export` | Export risk register |

---

## 9. Environment Variables Reference

```env
# -- Application ------------------------------------------------------
APP_ENV=development          # development | production
SECRET_KEY=                  # cryptographically random 64-byte hex string; required
DATABASE_URL=                # sqlite:///./jec.db  OR  postgresql://user:pass@host/db
REDIS_URL=redis://localhost:6379/0
TEST_MODE=false              # true enables deterministic fixture responses in all checks

# -- Microsoft / SharePoint -------------------------------------------
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=
SHAREPOINT_SITE_URL=         # e.g. https://contoso.sharepoint.com/sites/compliance
SHAREPOINT_DRIVE_ID=         # Graph drive ID for the evidence document library

# -- Google Workspace -------------------------------------------------
GOOGLE_SERVICE_ACCOUNT_JSON= # absolute path to service account key JSON file

# -- GitHub -----------------------------------------------------------
GITHUB_TOKEN=
GITHUB_ORG=

# -- AWS --------------------------------------------------------------
AWS_ROLE_ARN=                # read-only compliance IAM role ARN
AWS_REGION=us-east-1

# -- Okta (optional) --------------------------------------------------
OKTA_DOMAIN=                 # e.g. yourorg.okta.com  (omit if not using Okta)
OKTA_API_TOKEN=

# -- Notifications (optional) -----------------------------------------
SMTP_HOST=                   # for email notifications; omit to disable email
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFY_FROM_ADDRESS=         # e.g. compliance@jec.com
```

---

## 10. Local Run Instructions

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env - minimum required: SECRET_KEY and DATABASE_URL

# 4. Apply database migrations
alembic upgrade head

# 5. Seed initial control set
python scripts/seed_controls.py

# 6. Start the application
python -m uvicorn app.main:app --reload --port 8080
```

- App: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`
- Health: `http://localhost:8080/api/v1/health`

---

## 11. Docker Compose Services

| Service | Image | Purpose |
|---|---|---|
| `app` | Local Dockerfile | FastAPI application |
| `db` | postgres:16-alpine | PostgreSQL (production parity in dev) |
| `redis` | redis:7-alpine | Cache; reserved for future async job queue |

---

## 12. Production Readiness Checklist

- [ ] `APP_ENV=production` set
- [ ] `DATABASE_URL` points to PostgreSQL 16
- [ ] `SECRET_KEY` is a cryptographically random 64-byte hex string (not the dev placeholder)
- [ ] All integration secrets configured and connectivity verified
- [ ] HTTPS enforced at reverse proxy or load balancer; `secure=True` on session cookie
- [ ] `alembic upgrade head` runs in deploy step before app starts
- [ ] Rate limiting enabled and smoke-tested
- [ ] Audit log table on a backup schedule separate from main DB backup
- [ ] SharePoint locked evidence folder write access restricted to the service account only
- [ ] No `.env` baked into the Docker image; secrets injected at runtime
- [ ] Structured JSON logging to stdout; log aggregation configured
- [ ] Health endpoint monitored by uptime service
- [ ] Integration sync schedules verified running in production
- [ ] `TEST_MODE=false` in production
- [ ] Compatibility alias routes documented for removal in next release

---

## 13. Engineering Backlog by Phase

### Phase 1 - Foundation
- [ ] SQLAlchemy declarative model files for all new tables (integer PKs)
- [ ] Alembic migration: add new tables; ALTER existing tables where needed; do not break `auth.py`
- [ ] Control seed script (idempotent)
- [ ] Database session factory with env URL switching
- [ ] Pydantic Settings config

### Phase 2 - Check Engine
- [ ] `BaseCheck`, `CheckResult`, `CheckRegistry`
- [ ] `CheckRunner` with DB writes and task creation
- [ ] APScheduler setup in FastAPI lifespan
- [ ] `TEST_MODE` fixture injection
- [ ] 9 check modules (8 real + 1 manual stub)
- [ ] Manual check trigger endpoint under `/api/v1/`
- [ ] Service account detection rule applied during integration sync (see Section 14.5); flag candidates in snapshots; exclude from MFA compliance calculations; surface in Integrations page for human review

### Phase 3 - Integrations
- [ ] `IntegrationBase` contract
- [ ] SharePoint provider (upload, download, lock copy, download URL per tenant policy)
- [ ] Google Workspace provider
- [ ] GitHub provider
- [ ] AWS provider
- [ ] Okta provider (conditional on env vars)
- [ ] Integration health endpoint
- [ ] Manual sync trigger endpoint

### Phase 4 - Evidence Pipeline
- [ ] Upload endpoint (MIME validation, hash, SharePoint write)
- [ ] Accept / reject / flag endpoints
- [ ] Lock endpoint (hash verify, SharePoint copy, immutable)
- [ ] Evidence expiry APScheduler job
- [ ] Download endpoint

### Phase 5 - Audit Workflow
- [x] Audit period creation
- [x] Audit creation with control defaulting
- [x] Auditor assignment with expiry
- [x] Status transition endpoint
- [x] Auditor scope dependency
- [x] "View as auditor" preview endpoint
- [x] Export ZIP generation (streaming)

### Phase 6 - PBC Requests
- [x] Request creation (auditor + compliance manager)
- [x] Internal assignment endpoint
- [x] Evidence attachment endpoint
- [x] Auditor status update endpoint
- [x] Threaded comment endpoint
- [x] Overdue APScheduler job

### Phase 7 - Readiness Engines
- [x] Type I engine with `readiness_snapshots` and `readiness_gaps` writes
- [x] Type II engine with gap timeline and snapshot writes
- [x] Readiness API endpoints
- [x] Snapshot inclusion in audit export

### Phase 8 - Frontend (16 pages)
- [ ] Login (MSAL redirect)
- [ ] Dashboard + Chart.js widgets
- [x] Controls inventory
- [x] Control detail
- [x] Evidence locker + upload + detail
- [ ] Integrations
- [ ] Tasks
- [x] Audits overview + audit detail
- [x] Auditor portal (scoped)
- [x] PBC requests
- [ ] Reports / export
- [ ] Settings / RBAC
- [ ] Audit log viewer
- [ ] Update all fetch() calls to `/api/v1/` paths as each page is rebuilt

### Phase 9 - Security
- [x] `require_role` FastAPI dependency
- [x] `require_audit_scope` FastAPI dependency
- [ ] CSRF middleware
- [ ] Rate limiting middleware (`slowapi`)
- [ ] MIME type validation (`python-magic`)
- [ ] Audit log writes for all listed events
- [ ] Session cookie hardening

### Phase 3b - Policy Management
- [ ] `policies`, `policy_controls`, `policy_versions` models and migration
- [ ] Policy CRUD endpoints
- [ ] Policy approval workflow
- [ ] Policy version upload
- [ ] Policy-to-control linking
- [ ] APScheduler job for policy review reminders
- [ ] Readiness engine update to include policy coverage
- [ ] Policies list + detail frontend pages
- [ ] `policy_consistency_flags` table and migration
- [ ] APScheduler job for policy-vs-control consistency checks (see Section 14.5 rules)
- [ ] Consistency flag surface on Policy detail page and dashboard widget

### Phase 3c - Access Reviews
- [ ] `access_reviews`, `access_review_accounts` models and migration
- [ ] Review creation and account population from snapshots
- [ ] Per-account decision endpoints
- [ ] Risk flagging for terminated/department-changed accounts
- [ ] Remediation task creation on revoke decision
- [ ] Auto evidence generation on completion
- [ ] Access reviews frontend page

### Phase 3d - Personnel Compliance
- [ ] `personnel`, `personnel_requirements`, `personnel_compliance_records` models and migration
- [ ] Personnel sync from Google Workspace provider
- [ ] Requirement management endpoints
- [ ] Compliance record update + certificate upload
- [ ] APScheduler job for overdue tracking
- [ ] Personnel compliance + my-compliance frontend pages

### Phase 3e - Risk Register
- [ ] `risks`, `risk_controls`, `risk_history` models and migration
- [ ] Risk CRUD + review cycle endpoints
- [ ] Risk register export (PDF or CSV)
- [ ] Replace CC9.1 manual stub with `risk_register_check`
- [ ] Risk register frontend page

### Phase 10 - Tests
- [ ] `conftest.py` with per-role authenticated fixtures
- [ ] All unit tests
- [ ] All integration tests
- [ ] Tests for policy readiness coverage
- [ ] Tests for access review auto-evidence generation
- [ ] Tests for personnel compliance overdue logic
- [ ] Tests for risk register check
- [ ] CI pipeline configuration

---

## 14. Known Gaps and Future Roadmap

This section categorises every known gap against Vanta feature parity, plus internal technical debt items.

### 14.1 High Priority - Required Before First Real Audit

| Item | Gap vs Vanta | Notes |
|---|---|---|
| Full AICPA SOC 2 control set (~60 criteria) | Vanta ships all TSC criteria out of the box | MVP seeds 10; the remaining ~50 CC, A, PI, P, C criteria must be added before any audit engagement; this is the single most important gap |
| Policy management (Phase 3b) | Vanta ships policy templates and approval workflow | Written policies are a distinct SOC 2 artifact; they cannot be substituted with operational evidence; must be in place before audit |
| Access reviews (Phase 3c) | Vanta has a full access review module with SLA tracking | Required for CC6.2, CC6.3, CC6.6; quarterly reviews are expected by auditors |
| Evidence mapped to multiple controls | Vanta automatically cross-maps evidence across controls and frameworks | Current one-to-one schema forces duplication; `evidence_controls` junction table required |
| Email / notification system | Vanta sends email alerts for failing controls, expiring evidence, overdue tasks | Without notifications, compliance managers rely entirely on dashboard polling; overdue items will be missed |

### 14.2 Medium Priority - Required Before Type II Audit

| Item | Gap vs Vanta | Notes |
|---|---|---|
| Personnel compliance tracking (Phase 3d) | Vanta tracks training, background checks, device compliance per employee | Required for CC1.4, CC1.5; auditors ask for evidence that all staff completed security training |
| Risk register (Phase 3e) | Vanta has a full risk management module with scoring and history | CC9.1 is currently a manual stub; a real risk register with documented risks and annual review is required |
| Configurable Type II tolerance thresholds | Vanta allows per-control configuration | Failure rate % and gap day thresholds are hardcoded; make configurable before first Type II engagement |
| Evidence bulk upload | Not a Vanta gap - internal onboarding need | Batch ZIP upload for loading historical evidence during initial onboarding |
| SOC 2 report narrative PDF | Vanta generates formatted reports | Formatted PDF output for final audit deliverable; needed at report-issuance stage |

### 14.3 Lower Priority - Post-Audit Hardening

| Item | Gap vs Vanta | Notes |
|---|---|---|
| Real-time / webhook-driven checks | Vanta uses continuous monitoring; JEC uses periodic APScheduler | For most controls, periodic checks are sufficient; real-time is a future improvement |
| Integration extensibility / plugin registry | Vanta has 400+ integrations and a Private Integrations API | JEC has 5 hardcoded providers; adding a sixth requires code changes; a plugin registry would allow configuration-driven integration |
| Compatibility alias route retirement | Internal technical debt | Remove old non-`/api/v1/` routes once all frontend pages are updated in Phase 8 |
| WORM / storage-level audit log immutability | Vanta uses append-only storage | Application-level rules are sufficient now; WORM bucket or DB-level enforcement is a future hardening item |
| Redis-backed async job queue | Internal architecture | Replace in-process APScheduler if check engine or integration sync scale requires it |
| UUID primary keys | Internal schema | Current integer IDs are fine; revisit only if multi-instance federation is needed |

### 14.4 Out of Scope for This Product

| Item | Notes |
|---|---|
| AI questionnaire automation | Vanta AI answers security questionnaires automatically; not planned for JEC internal tool |
| Public trust center | Vanta lets companies share compliance status publicly; deferred until audit workflow is stable and proven |
| Non-SOC 2 frameworks | HIPAA, ISO 27001, GDPR - only after SOC 2 is complete |
| Third-party risk management portal | Vanta has a full vendor onboarding and assessment module; only add if required for a specific SOC 2 evidence gap (CC9.2) |
| Device compliance monitoring | Vanta Device Monitor tracks endpoint configuration; not in scope; would require MDM integration |
| Multi-tenant SaaS billing | Internal tool only |
| Questionnaire response library | Vanta builds a reusable answer library over time; not planned |

### 14.5 Vanta Compliance Agent - What Is and Is Not Applicable to JEC

Vanta released the Compliance Agent in March 2026. It positions itself as a "24/7 GRC engineer" with four specific capabilities. This section records an honest assessment of each against the JEC platform.

**Capability 1: Full program awareness recommendations**
The agent draws context across all frameworks, controls, and policies and surfaces prioritised recommendations grounded in the full trust program.

JEC position: OUT OF SCOPE. This requires running an LLM continuously against compliance data. The JEC platform does not include an AI inference layer and is not planned to. The check engine, gap timeline, and dashboard serve a similar orientation function through deterministic rules rather than AI inference.

**Capability 2: AI service account detection**
The agent scans user accounts from integrations, identifies likely service accounts (non-human accounts that should not be treated as user compliance signals), surfaces them for review, and pauses irrelevant compliance tasks against them.

JEC position: ACHIEVABLE WITHOUT AI - add to Phase 2. The JEC system already pulls user account data from Google Workspace, GitHub, and AWS into integration_snapshots. A deterministic classification rule applied during the integration sync can flag service accounts without an LLM:

Rule: flag an account as a likely service account if two or more of the following are true:
- display name contains: bot, svc, service, api, deploy, ci, automation, github-actions, terraform
- no MFA enrollment recorded
- no last_login within 90 days
- no matching personnel record by email

Flagged accounts are stored with a new column `is_service_account_candidate BOOLEAN` on the integration_snapshots row (or a separate `service_account_candidates` table). They appear in the Integrations page for human review and are excluded from MFA compliance calculations until confirmed or dismissed.

This prevents a service account appearing as a failing MFA check for a human user and polluting the CC6.1 readiness signal - exactly the problem Vanta's agent solves, without requiring AI.

**Capability 3: Policy-to-program consistency checks**
The agent detects contradictions between what written policies state and what the actual control checks and program activity show.

JEC position: ACHIEVABLE WITHOUT AI - add to Phase 3b. A deterministic consistency check can be added to the policy management phase as a scheduled job. The job joins the policies table against control_checks for every control linked via policy_controls:

Rules to check:
- If a policy states a review frequency (e.g., "MFA reviewed monthly") and the linked control has no passing check within that period: flag as INCONSISTENT
- If a policy has status='approved' but its linked control has type2_status='failing': flag as INCONSISTENT
- If a policy has next_review_date in the past and status is not 'needs_review': flag as OVERDUE and set status='needs_review'
- If a policy document references a control code that does not exist in the controls table: flag as UNMAPPED

Results are written to a new `policy_consistency_flags` table and surfaced as a dashboard widget ("X policies have consistency issues") and in the Policy detail page. No LLM required.

**Capability 4: AI-driven remediation guidance**
The agent provides specific corrective action recommendations inside the platform when issues are identified.

JEC position: OUT OF SCOPE. Generating context-aware remediation guidance requires an LLM. The JEC platform instead provides static remediation guidance text stored per control in evidence_requirements and per check module in the result_summary field. This is less dynamic but sufficient for an internal tool where the compliance manager knows the context.

**Architecture note:** The decisions in v2.3 - check engine, integration snapshots, policy table, evidence_controls, gap timeline - are the correct foundation if the team ever wants to layer AI-driven analysis on top. Nothing in the current architecture blocks adding an LLM inference step later. The check engine result_summary fields and policy_consistency_flags table would be natural inputs to an AI layer if that decision is made in a future phase.
