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


class Phase7ReadinessTests(unittest.TestCase):
    def _env_for(self, db_path: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
        env["PYTHONPATH"] = str(ROOT)
        env["TEST_MODE"] = "true"
        return env

    def test_readiness_snapshots_and_gaps_are_persisted(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        db_path = SCRATCH / f"phase7_readiness_{uuid.uuid4().hex}.db"
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
                from datetime import datetime, timezone
                from io import BytesIO
                import zipfile
                from fastapi.testclient import TestClient

                from app.auth import create_session_token
                from app.db import engine, get_connection
                from app.main import app

                with get_connection() as conn:
                    conn.execute("INSERT INTO frameworks (id, name, version) VALUES (970, 'Phase7', '1')")
                    conn.execute("INSERT INTO controls (id, framework_id, control_id, control_code, title, description, is_automated, frequency, type1_status, type2_status) VALUES (970, 970, 'P7.1', 'P7.1', 'Automated Control', 'Automated control', 1, 'monthly', 'implemented', 'operating')")
                    conn.execute("INSERT INTO controls (id, framework_id, control_id, control_code, title, description, is_automated, frequency, type1_status, type2_status) VALUES (971, 970, 'P7.2', 'P7.2', 'Manual Control', 'Manual control', 0, 'monthly', 'not_started', 'not_started')")
                    conn.execute("INSERT INTO controls (id, framework_id, control_id, control_code, title, description, is_automated, frequency, type1_status, type2_status) VALUES (972, 970, 'P7.3', 'P7.3', 'Type II Control', 'Type II control', 1, 'monthly', 'implemented', 'operating')")
                    conn.execute("INSERT INTO users (id, oid, email, name, role) VALUES (970, 'cm7', 'cm7@example.com', 'CM7', 'compliance_manager')")
                    conn.execute("INSERT INTO audit_periods (id, framework_id, name, report_type, point_in_time_date, observation_start, observation_end, created_by) VALUES (970, 970, 'Phase7 Type I', 'type1', '2026-03-31T00:00:00+00:00', NULL, NULL, 970)")
                    conn.execute("INSERT INTO audit_periods (id, framework_id, name, report_type, point_in_time_date, observation_start, observation_end, created_by) VALUES (971, 970, 'Phase7 Type II', 'type2', NULL, '2026-01-01T00:00:00+00:00', '2026-03-31T00:00:00+00:00', 970)")
                    conn.execute("INSERT INTO audits (id, period_id, audit_period_id, audit_firm, status, fieldwork_start, fieldwork_end, created_by) VALUES (970, 970, 970, 'CPA', 'fieldwork', '2026-04-01T00:00:00+00:00', '2026-04-30T00:00:00+00:00', 970)")
                    conn.execute("INSERT INTO audits (id, period_id, audit_period_id, audit_firm, status, fieldwork_start, fieldwork_end, created_by) VALUES (971, 971, 971, 'CPA', 'fieldwork', '2026-04-01T00:00:00+00:00', '2026-04-30T00:00:00+00:00', 970)")
                    conn.execute("INSERT INTO audit_controls (audit_id, control_id, in_scope) VALUES (970, 970, 1)")
                    conn.execute("INSERT INTO audit_controls (audit_id, control_id, in_scope) VALUES (970, 971, 1)")
                    conn.execute("INSERT INTO audit_controls (audit_id, control_id, in_scope) VALUES (971, 972, 1)")
                    conn.execute("INSERT INTO control_checks (control_id, checked_at, result, details, check_name, status, result_summary, run_at, triggered_by) VALUES (970, '2026-03-15T00:00:00+00:00', 'pass', '{}', 'Phase7 Check', 'pass', 'Passed before PIT', '2026-03-15T00:00:00+00:00', 'test')")
                    conn.execute("INSERT INTO control_checks (control_id, checked_at, result, details, check_name, status, result_summary, run_at, triggered_by) VALUES (972, '2026-01-15T00:00:00+00:00', 'pass', '{}', 'Phase7 Check', 'pass', 'January pass', '2026-01-15T00:00:00+00:00', 'test')")
                    conn.execute("INSERT INTO control_checks (control_id, checked_at, result, details, check_name, status, result_summary, run_at, triggered_by) VALUES (972, '2026-03-15T00:00:00+00:00', 'pass', '{}', 'Phase7 Check', 'pass', 'March pass', '2026-03-15T00:00:00+00:00', 'test')")
                    conn.execute("INSERT INTO evidence (id, control_id, name, source, artifact_path, collected_at, title, source_type, status, valid_from, valid_to, file_name, file_size_bytes) VALUES (970, 970, 'Valid Evidence', 'manual', 'valid.pdf', '2026-01-01T00:00:00+00:00', 'Valid Evidence', 'manual', 'locked', '2026-01-01T00:00:00+00:00', NULL, 'valid.pdf', 10)")
                    conn.execute("INSERT INTO evidence (id, control_id, name, source, artifact_path, collected_at, title, source_type, status, valid_from, valid_to, file_name, file_size_bytes) VALUES (971, 972, 'January Evidence', 'manual', 'jan.pdf', '2026-01-01T00:00:00+00:00', 'January Evidence', 'manual', 'locked', '2026-01-01T00:00:00+00:00', '2026-01-31T23:59:59+00:00', 'jan.pdf', 10)")
                    conn.execute("INSERT INTO evidence_controls (evidence_id, control_id, is_primary) VALUES (970, 970, 1)")
                    conn.execute("INSERT INTO evidence_controls (evidence_id, control_id, is_primary) VALUES (971, 972, 1)")

                cm = {"session": create_session_token({"oid": "cm7"})}

                with TestClient(app) as client:
                    type1 = client.get("/api/v1/audits/970/readiness/type1", cookies=cm)
                    assert type1.status_code == 200, type1.text
                    type1_payload = type1.json()
                    assert type1_payload["overall_score"] == 50.0, type1_payload
                    by_code = {item["control_code"]: item for item in type1_payload["controls"]}
                    assert by_code["P7.1"]["readiness_status"] == "Ready"
                    assert by_code["P7.2"]["readiness_status"] == "Not Ready"
                    assert any(gap["gap_type"] == "missing_evidence" for gap in type1_payload["gaps"])

                    type2 = client.get("/api/v1/audits/971/readiness/type2", cookies=cm)
                    assert type2.status_code == 200, type2.text
                    type2_payload = type2.json()
                    assert type2_payload["overall_score"] == 0.0, type2_payload
                    assert type2_payload["controls"][0]["effectiveness_status"] == "Not Effective"
                    assert any(gap["gap_type"] == "missing_monthly_evidence" and gap["severity"] == "red" for gap in type2_payload["gaps"])

                    export = client.post("/api/v1/audits/971/export", cookies=cm)
                    assert export.status_code == 200, export.text
                    with zipfile.ZipFile(BytesIO(export.content)) as archive:
                        names = set(archive.namelist())
                    assert "readiness/type1_snapshot.json" in names
                    assert "readiness/type2_snapshot.json" in names

                with get_connection() as conn:
                    snapshots = conn.execute("SELECT report_type FROM readiness_snapshots ORDER BY id").fetchall()
                    gaps = conn.execute("SELECT gap_type, severity FROM readiness_gaps ORDER BY id").fetchall()
                snapshot_types = [row["report_type"] for row in snapshots]
                assert "type1" in snapshot_types
                assert "type2" in snapshot_types
                assert any(row["gap_type"] == "missing_evidence" for row in gaps)
                assert any(row["gap_type"] == "missing_monthly_evidence" and row["severity"] == "red" for row in gaps)
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
