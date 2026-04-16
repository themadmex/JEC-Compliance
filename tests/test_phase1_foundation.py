from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / ".test-data"


class Phase1FoundationTests(unittest.TestCase):
    def _env_for(self, db_path: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
        env["PYTHONPATH"] = str(ROOT)
        return env

    def test_clean_sqlite_migration_creates_phase1_schema(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        db_path = SCRATCH / f"phase1_schema_{uuid.uuid4().hex}.db"
        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=ROOT,
                env=self._env_for(db_path),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            with sqlite3.connect(db_path) as conn:
                table_names = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                for required_table in {
                    "check_evidence",
                    "audit_users",
                    "audit_comments",
                    "readiness_snapshots",
                    "readiness_gaps",
                }:
                    self.assertIn(required_table, table_names)

                control_columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(controls)")
                }
                for required_column in {
                    "control_code",
                    "category",
                    "frequency",
                    "is_automated",
                    "type1_status",
                    "type2_status",
                    "evidence_requirements",
                }:
                    self.assertIn(required_column, control_columns)
        finally:
            pass

    def test_seed_controls_is_idempotent_and_seeds_prd_controls(self) -> None:
        SCRATCH.mkdir(exist_ok=True)
        db_path = SCRATCH / f"phase1_seed_{uuid.uuid4().hex}.db"
        try:
            env = self._env_for(db_path)

            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            for _ in range(2):
                result = subprocess.run(
                    [sys.executable, "scripts/seed_controls.py"],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            with sqlite3.connect(db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT control_code, title, type1_status, type2_status,
                           evidence_requirements
                    FROM controls
                    ORDER BY control_code
                    """
                ).fetchall()

            self.assertEqual(len(rows), 10)
            self.assertEqual(
                [row[0] for row in rows],
                [
                    "A1.1",
                    "CC6.1",
                    "CC6.2",
                    "CC6.3",
                    "CC6.6",
                    "CC7.1",
                    "CC7.2",
                    "CC8.1",
                    "CC9.1",
                    "P1.1",
                ],
            )
            self.assertTrue(all(row[2] == "not_started" for row in rows))
            self.assertTrue(all(row[3] == "not_started" for row in rows))
            self.assertTrue(all(row[4] for row in rows))
        finally:
            pass


if __name__ == "__main__":
    unittest.main()
