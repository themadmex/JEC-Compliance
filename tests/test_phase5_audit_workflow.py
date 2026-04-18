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


class Phase5AuditWorkflowTests(unittest.TestCase):
    def _env_for(self, db_path: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
        env["PYTHONPATH"] = str(ROOT)
        env["TEST_MODE"] = "true"
        return env

    def test_audit_workflow_scope_request_export(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        db_path = SCRATCH / f"phase5_audit_{uuid.uuid4().hex}.db"
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
                from fastapi.testclient import TestClient

                from app.auth import create_session_token
                from app.db import engine, get_connection
                from app.main import app
                import app.routes.evidence as evidence_route

                evidence_route.sharepoint.is_configured = lambda: False

                with get_connection() as conn:
                    conn.execute("INSERT INTO frameworks (id, name, version) VALUES (1, 'SOC2', '2017')")
                    conn.execute("INSERT INTO controls (id, framework_id, control_id, title, description) VALUES (1, 1, 'CC1.1', 'Control 1', 'Control description one')")
                    conn.execute("INSERT INTO controls (id, framework_id, control_id, title, description) VALUES (2, 1, 'CC2.1', 'Control 2', 'Control description two')")
                    conn.execute("INSERT INTO users (id, oid, email, name, role) VALUES (1, 'cm', 'cm@example.com', 'CM', 'compliance_manager')")
                    conn.execute("INSERT INTO users (id, oid, email, name, role) VALUES (2, 'aud', 'aud@example.com', 'Auditor', 'auditor')")

                cm = {"session": create_session_token({"oid": "cm"})}
                aud = {"session": create_session_token({"oid": "aud"})}
                pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"

                with TestClient(app) as client:
                    period = client.post("/api/v1/audit-periods", cookies=cm, json={
                        "framework_id": 1,
                        "name": "FY26 Type II",
                        "report_type": "type2",
                        "observation_start": "2026-01-01T00:00:00Z",
                        "observation_end": "2026-03-31T00:00:00Z",
                    })
                    assert period.status_code == 201, period.text
                    audit = client.post("/api/v1/audits", cookies=cm, json={
                        "period_id": period.json()["id"],
                        "audit_firm": "Example CPA",
                        "fieldwork_start": "2026-04-01T00:00:00Z",
                        "fieldwork_end": "2026-04-30T00:00:00Z",
                    })
                    assert audit.status_code == 201, audit.text
                    audit_id = audit.json()["id"]

                    scoped = client.patch(f"/api/v1/audits/{audit_id}/controls/2", cookies=cm, json={"in_scope": False})
                    assert scoped.status_code == 200, scoped.text
                    assert scoped.json()["in_scope"] in (0, False)

                    assignment = client.post(f"/api/v1/audits/{audit_id}/auditors", cookies=cm, json={"user_id": 2})
                    assert assignment.status_code == 201, assignment.text

                    request = client.post(f"/api/v1/audits/{audit_id}/requests", cookies=aud, json={
                        "title": "Please provide evidence",
                        "description": "Need a sample",
                        "control_id": 1,
                        "request_type": "sample",
                        "sample_size": 1,
                    })
                    assert request.status_code == 201, request.text
                    request_id = request.json()["id"]

                    assert client.post(f"/api/v1/requests/{request_id}/comments", cookies=cm, json={"body": "Internal note", "is_internal": True}).status_code == 201
                    assert client.post(f"/api/v1/requests/{request_id}/comments", cookies=aud, json={"body": "Auditor note"}).status_code == 201
                    auditor_detail = client.get(f"/api/v1/requests/{request_id}", cookies=aud)
                    assert auditor_detail.status_code == 200, auditor_detail.text
                    assert len(auditor_detail.json()["comments"]) == 1

                    upload = client.post("/evidence/upload", cookies=cm, data={
                        "control_id": "1",
                        "title": "Locked Evidence",
                        "source_type": "manual",
                        "valid_from": "2026-02-01",
                        "valid_to": "2026-03-01",
                    }, files={"file": ("locked.pdf", pdf, "application/pdf")})
                    assert upload.status_code == 201, upload.text
                    evidence_id = upload.json()["id"]
                    assert client.patch(f"/evidence/{evidence_id}/accept", cookies=cm).status_code == 200
                    assert client.patch(f"/evidence/{evidence_id}/lock", cookies=cm).status_code == 200
                    assert client.post(f"/api/v1/requests/{request_id}/evidence", cookies=cm, json={"evidence_id": evidence_id}).status_code == 200
                    assert client.get(f"/api/v1/audits/{audit_id}/preview-as-auditor", cookies=cm).status_code == 200
                    assert client.get(f"/api/v1/audits/{audit_id}/readiness/type2", cookies=cm).status_code == 200
                    export = client.post(f"/api/v1/audits/{audit_id}/export", cookies=cm)
                    assert export.status_code == 200, export.text
                    assert export.headers["content-type"].startswith("application/zip")

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
            for path in (ROOT / "artifacts").glob("*_locked.pdf"):
                path.unlink(missing_ok=True)
            for path in (ROOT / "artifacts" / "exports").glob("export_*.zip"):
                path.unlink(missing_ok=True)
