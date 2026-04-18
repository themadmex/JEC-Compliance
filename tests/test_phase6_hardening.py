from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / ".test-data"


class Phase6HardeningTests(unittest.TestCase):
    def _env_for(self, db_path: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
        env["PYTHONPATH"] = str(ROOT)
        env["TEST_MODE"] = "true"
        return env

    def test_pre_phase6_security_contract(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        db_path = SCRATCH / f"phase6_hardening_{uuid.uuid4().hex}.db"
        env = self._env_for(db_path)
        try:
            migration = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(migration.returncode, 0, migration.stderr + migration.stdout)

            script = textwrap.dedent(
                r"""
                from datetime import datetime, timedelta, timezone
                from fastapi.testclient import TestClient

                import app.repository as repository
                from app.auth import create_session_token
                from app.db import engine, get_connection
                from app.main import app
                import app.routes.evidence as evidence_route

                evidence_route.sharepoint.is_configured = lambda: False

                with get_connection() as conn:
                    conn.execute("INSERT INTO frameworks (id, name, version) VALUES (991, 'Phase6', '1')")
                    conn.execute("INSERT INTO controls (id, framework_id, control_id, title, description) VALUES (991, 991, 'P6.1', 'Phase6 Control 1', 'Control description one')")
                    conn.execute("INSERT INTO controls (id, framework_id, control_id, title, description) VALUES (992, 991, 'P6.2', 'Phase6 Control 2', 'Control description two')")
                    conn.execute("INSERT INTO users (id, oid, email, name, role, scoped_token, token_expires_at) VALUES (991, 'cm6', 'cm6@example.com', 'CM6', 'compliance_manager', NULL, NULL)")
                    conn.execute("INSERT INTO users (id, oid, email, name, role, scoped_token, token_expires_at) VALUES (992, 'aud6', 'aud6@example.com', 'Auditor6', 'auditor', 'aud-token-6', '2099-01-01T00:00:00+00:00')")
                    conn.execute("INSERT INTO users (id, oid, email, name, role, scoped_token, token_expires_at) VALUES (993, 'con6', 'con6@example.com', 'Contributor6', 'contributor', NULL, NULL)")
                    conn.execute("INSERT INTO users (id, oid, email, name, role, scoped_token, token_expires_at) VALUES (994, 'aud7', 'aud7@example.com', 'Auditor7', 'auditor', NULL, NULL)")

                cm = {"session": create_session_token({"oid": "cm6"})}
                aud = {"session": create_session_token({"oid": "aud6"})}
                contributor = {"session": create_session_token({"oid": "con6"})}
                auditor_headers = {"X-Auditor-Token": "aud-token-6"}

                with TestClient(app) as client:
                    assert client.get("/controls").status_code == 401
                    assert client.get("/api/v1/checks").status_code == 401
                    assert client.post("/jobs/run-evidence-check").status_code == 401
                    assert client.get("/sharepoint/status").status_code == 401
                    assert client.get("/integrations/status").status_code == 401

                    period1 = client.post("/api/v1/audit-periods", cookies=cm, json={
                        "framework_id": 991,
                        "name": "Assigned Audit",
                        "report_type": "type2",
                        "observation_start": "2026-01-01T00:00:00Z",
                        "observation_end": "2026-03-31T00:00:00Z",
                    })
                    assert period1.status_code == 201, period1.text
                    period2 = client.post("/api/v1/audit-periods", cookies=cm, json={
                        "framework_id": 991,
                        "name": "Unassigned Audit",
                        "report_type": "type2",
                        "observation_start": "2026-04-01T00:00:00Z",
                        "observation_end": "2026-06-30T00:00:00Z",
                    })
                    assert period2.status_code == 201, period2.text

                    audit1 = client.post("/api/v1/audits", cookies=cm, json={
                        "period_id": period1.json()["id"],
                        "audit_firm": "CPA One",
                        "fieldwork_start": "2026-04-01T00:00:00Z",
                        "fieldwork_end": "2026-04-30T00:00:00Z",
                    })
                    assert audit1.status_code == 201, audit1.text
                    audit2 = client.post("/api/v1/audits", cookies=cm, json={
                        "period_id": period2.json()["id"],
                        "audit_firm": "CPA Two",
                        "fieldwork_start": "2026-07-01T00:00:00Z",
                        "fieldwork_end": "2026-07-31T00:00:00Z",
                    })
                    assert audit2.status_code == 201, audit2.text
                    audit_id = audit1.json()["id"]

                    assignment = client.post(f"/api/v1/audits/{audit_id}/auditors", cookies=cm, json={"user_id": 992})
                    assert assignment.status_code == 201, assignment.text
                    assert assignment.json()["scoped_token"] == "aud-token-6"

                    eligible_auditors = client.get("/api/v1/auditors", cookies=cm)
                    assert eligible_auditors.status_code == 200, eligible_auditors.text
                    assert {row["id"] for row in eligible_auditors.json()} == {992, 994}

                    generated_assignment = client.post(f"/api/v1/audits/{audit_id}/auditors", cookies=cm, json={"user_id": 994})
                    assert generated_assignment.status_code == 201, generated_assignment.text
                    generated_token = generated_assignment.json()["scoped_token"]
                    assert generated_token
                    assert generated_assignment.json()["access_expires_at"]
                    assigned_auditors = client.get(f"/api/v1/audits/{audit_id}/auditors", cookies=cm)
                    assert assigned_auditors.status_code == 200, assigned_auditors.text
                    assert {row["user_id"] for row in assigned_auditors.json()} == {992, 994}
                    revoke = client.delete(f"/api/v1/audits/{audit_id}/auditors/994", cookies=cm)
                    assert revoke.status_code == 204, revoke.text
                    revoked_detail = client.get(f"/api/v1/audits/{audit_id}", headers={"X-Auditor-Token": generated_token})
                    assert revoked_detail.status_code == 403, revoked_detail.text

                    audits_for_auditor = client.get("/api/v1/audits", cookies=aud)
                    assert audits_for_auditor.status_code == 200, audits_for_auditor.text
                    assert [row["id"] for row in audits_for_auditor.json()] == [audit_id]

                    scoped_detail = client.get(f"/api/v1/audits/{audit_id}", headers=auditor_headers)
                    assert scoped_detail.status_code == 200, scoped_detail.text
                    token_profile = client.get("/auth/me", headers=auditor_headers)
                    assert token_profile.status_code == 200, token_profile.text
                    assert token_profile.json()["role"] == "auditor"
                    assert client.get(f"/api/v1/audits/{audit2.json()['id']}", headers=auditor_headers).status_code == 403
                    assert client.get("/evidence", cookies=aud).status_code == 403

                    request = client.post(f"/api/v1/audits/{audit_id}/requests", cookies=aud, json={
                        "title": "Evidence for scoped control",
                        "control_id": 991,
                    })
                    assert request.status_code == 201, request.text
                    request_id = request.json()["id"]

                    overdue_request = client.post(f"/api/v1/audits/{audit_id}/requests", cookies=cm, json={
                        "title": "Past due PBC request",
                        "control_id": 991,
                        "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    })
                    assert overdue_request.status_code == 201, overdue_request.text
                    overdue_count = repository.scan_overdue_audit_requests()
                    assert overdue_count == 1
                    overdue_detail = client.get(f"/api/v1/requests/{overdue_request.json()['id']}", cookies=cm)
                    assert overdue_detail.status_code == 200, overdue_detail.text
                    assert overdue_detail.json()["status"] == "overdue"
                    with get_connection() as conn:
                        overdue_logs = conn.execute(
                            "SELECT id FROM audit_log WHERE action = 'request.overdue' AND object_id = ?",
                            (overdue_request.json()["id"],),
                        ).fetchall()
                    assert len(overdue_logs) == 1

                    with get_connection() as conn:
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute(
                            "INSERT INTO evidence (id, control_id, name, source, artifact_path, collected_at, title, source_type, status, valid_from, file_name, file_size_bytes) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (991, 992, 'Wrong Control Evidence', 'manual', 'wrong.pdf', now, 'Wrong Control Evidence', 'manual', 'locked', now, 'wrong.pdf', 10),
                        )
                    bad_attach = client.post(f"/api/v1/requests/{request_id}/evidence", cookies=contributor, json={"evidence_id": 991})
                    assert bad_attach.status_code == 409, bad_attach.text

                    with get_connection() as conn:
                        now = datetime.now(timezone.utc).isoformat()
                        conn.execute(
                            "INSERT INTO evidence (id, control_id, name, source, artifact_path, collected_at, title, source_type, status, valid_from, file_name, file_size_bytes) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (992, 991, 'Right Control Evidence', 'manual', 'right.pdf', now, 'Right Control Evidence', 'manual', 'submitted', now, 'right.pdf', 10),
                        )
                    good_attach = client.post(f"/api/v1/requests/{request_id}/evidence", cookies=contributor, json={"evidence_id": 992})
                    assert good_attach.status_code == 200, good_attach.text
                    assert good_attach.json()["evidence"][0]["id"] == 992

                    token_comment = client.post(f"/api/v1/requests/{request_id}/comments", headers=auditor_headers, json={"body": "Looks good so far"})
                    assert token_comment.status_code == 201, token_comment.text
                    status_update = client.patch(f"/api/v1/requests/{request_id}", headers=auditor_headers, json={"status": "fulfilled"})
                    assert status_update.status_code == 200, status_update.text
                    assert status_update.json()["status"] == "fulfilled"

                    incomplete_export = client.post(f"/api/v1/audits/{audit_id}/export", cookies=cm)
                    assert incomplete_export.status_code == 409, incomplete_export.text

                engine.dispose()
                """
            )
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        finally:
            db_path.unlink(missing_ok=True)
            for path in (ROOT / "artifacts" / "exports").glob("export_*.zip"):
                path.unlink(missing_ok=True)
