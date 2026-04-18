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


class Phase2CheckEngineTests(unittest.IsolatedAsyncioTestCase):
    def _env_for(self, db_path: Path) -> dict[str, str]:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
        env["PYTHONPATH"] = str(ROOT)
        env["TEST_MODE"] = "true"
        return env

    def _prepare_db(self) -> Path:
        SCRATCH.mkdir(exist_ok=True)
        db_path = SCRATCH / f"phase2_checks_{uuid.uuid4().hex}.db"
        env = self._env_for(db_path)
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [sys.executable, "scripts/seed_controls.py"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        return db_path

    async def test_runner_writes_result_for_every_registered_check(self) -> None:
        db_path = self._prepare_db()
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
        os.environ["TEST_MODE"] = "true"

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.core.config import get_settings
        from app.services.checks.runner import CheckRunner, initialize_engine

        get_settings.cache_clear()
        database_url = f"sqlite:///{db_path.resolve().as_posix()}"
        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        initialize_engine()
        session = SessionLocal()
        try:
            results = await CheckRunner(session).run_all(triggered_by="test")
        finally:
            session.close()

        self.assertEqual(len(results), 10)
        with sqlite3.connect(db_path) as conn:
            check_count = conn.execute("SELECT COUNT(*) FROM control_checks").fetchone()[0]
            self.assertEqual(check_count, 10)
            statuses = {
                row[0] for row in conn.execute("SELECT DISTINCT status FROM control_checks")
            }
            self.assertIn("pass", statuses)
            self.assertIn("skipped", statuses)

    def test_service_account_classifier_matches_prd_rule(self) -> None:
        from app.services.checks.service_accounts import classify_service_account

        is_candidate, reason = classify_service_account(
            {
                "display_name": "Terraform Deploy Bot",
                "email": "terraform@jec.com",
                "mfa_enrolled": False,
                "last_login_days": 180,
            },
            matching_personnel_email=False,
        )

        self.assertTrue(is_candidate)
        self.assertIsNotNone(reason)


if __name__ == "__main__":
    unittest.main()
