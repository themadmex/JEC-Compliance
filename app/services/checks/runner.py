from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from time import perf_counter

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.checks.access import (
    AccessProvisioningCheck,
    BackupVerificationCheck,
    ManualGuidanceCheck,
    SecurityMonitoringCheck,
)
from app.services.checks.aws import ABACAccessCheck, AWSAdminAccessCheck
from app.services.checks.base import CheckResult, CheckStatus
from app.services.checks.github import GitHubBranchProtectionCheck, GitHubVulnerabilityCheck
from app.services.checks.mfa import GoogleMFACheck
from app.services.checks.registry import CheckRegistry, check_registry

logger = logging.getLogger(__name__)


def initialize_engine(registry: CheckRegistry = check_registry) -> CheckRegistry:
    """Register all Phase 2 checks in the global registry."""
    for check in [
        GoogleMFACheck(),
        AccessProvisioningCheck(),
        ABACAccessCheck(),
        AWSAdminAccessCheck(),
        GitHubVulnerabilityCheck(),
        SecurityMonitoringCheck(),
        GitHubBranchProtectionCheck(),
        BackupVerificationCheck(),
        ManualGuidanceCheck(
            "CC9.1",
            "Risk Assessment",
            "Manual risk assessment check skipped. Upload the current risk register and annual review evidence.",
        ),
        ManualGuidanceCheck(
            "P1.1",
            "Privacy Notice",
            "Manual privacy notice check skipped. Upload the current privacy notice and approval history.",
        ),
    ]:
        registry.register(check)
    logger.info("Compliance check engine initialized with %d checks.", len(registry.list_checks()))
    return registry


class CheckRunner:
    def __init__(self, db_session: Session, registry: CheckRegistry = check_registry) -> None:
        self.db_session = db_session
        self.registry = registry
        self.settings = get_settings()

    async def run_one(self, control_code: str, triggered_by: str = "manual") -> CheckResult | None:
        check = self.registry.get_check(control_code)
        if check is None:
            return None

        started = perf_counter()
        try:
            result = await check.run(test_mode=self.settings.test_mode, db_session=self.db_session)
        except Exception as exc:  # pragma: no cover - defensive boundary
            logger.exception("Check %s failed unexpectedly.", check.check_name)
            result = check.result(
                CheckStatus.ERROR,
                f"{check.name} errored before completion.",
                {"error": str(exc)},
                "Investigate the check implementation and integration credentials.",
            )
        duration_ms = int((perf_counter() - started) * 1000)

        control = self._get_control(control_code)
        if control is None:
            logger.error("Cannot persist check %s: control %s not found.", check.check_name, control_code)
            return result

        check_id = self._insert_control_check(control["id"], result, duration_ms, triggered_by)
        if result.status in {CheckStatus.FAIL, CheckStatus.ERROR}:
            task_id = self._ensure_remediation_task(control, result, check_id)
            self.db_session.execute(
                text("UPDATE control_checks SET created_task_id = :task_id WHERE id = :check_id"),
                {"task_id": task_id, "check_id": check_id},
            )
            self.db_session.execute(
                text(
                    """
                    UPDATE controls
                    SET type2_status = 'failing', last_tested_at = :run_at, updated_at = :run_at
                    WHERE id = :control_id
                    """
                ),
                {"control_id": control["id"], "run_at": result.run_at.isoformat()},
            )
        else:
            self.db_session.execute(
                text(
                    """
                    UPDATE controls
                    SET last_tested_at = :run_at, updated_at = :run_at
                    WHERE id = :control_id
                    """
                ),
                {"control_id": control["id"], "run_at": result.run_at.isoformat()},
            )

        self.db_session.commit()
        return result

    async def run_all(self, triggered_by: str = "scheduler") -> list[CheckResult]:
        results: list[CheckResult] = []
        for control_code in self.registry.list_controls():
            result = await self.run_one(control_code, triggered_by=triggered_by)
            if result is not None:
                results.append(result)
        return results

    def _get_control(self, control_code: str) -> dict[str, object] | None:
        row = self.db_session.execute(
            text(
                """
                SELECT id, control_code, control_id, title, owner_user_id
                FROM controls
                WHERE control_code = :control_code OR control_id = :control_code
                """
            ),
            {"control_code": control_code},
        ).mappings().first()
        return dict(row) if row else None

    def _insert_control_check(
        self,
        control_id: int,
        result: CheckResult,
        duration_ms: int,
        triggered_by: str,
    ) -> int:
        now = result.run_at.isoformat()
        returning = " RETURNING id" if self.db_session.bind.dialect.name == "postgresql" else ""
        cursor = self.db_session.execute(
            text(
                f"""
                INSERT INTO control_checks (
                    control_id, checked_at, result, details, check_name, status,
                    result_summary, result_detail, run_at, duration_ms, triggered_by
                )
                VALUES (
                    :control_id, :checked_at, :result, :details, :check_name, :status,
                    :result_summary, :result_detail, :run_at, :duration_ms, :triggered_by
                )
                {returning}
                """
            ),
            {
                "control_id": control_id,
                "checked_at": now,
                "result": result.status.value,
                "details": result.summary,
                "check_name": result.check_name,
                "status": result.status.value,
                "result_summary": result.summary,
                "result_detail": json.dumps(result.details, sort_keys=True),
                "run_at": now,
                "duration_ms": duration_ms,
                "triggered_by": triggered_by,
            },
        )
        if self.db_session.bind.dialect.name == "postgresql":
            return int(cursor.scalar_one())
        inserted_id = cursor.lastrowid
        if inserted_id is not None:
            return int(inserted_id)
        row = self.db_session.execute(text("SELECT last_insert_rowid() AS id")).mappings().one()
        return int(row["id"])

    def _ensure_remediation_task(
        self,
        control: dict[str, object],
        result: CheckResult,
        check_id: int,
    ) -> int:
        existing = self.db_session.execute(
            text(
                """
                SELECT id
                FROM tasks
                WHERE control_id = :control_id
                  AND type = 'remediation'
                  AND source_object_type = 'control_check'
                  AND title LIKE :title_prefix
                  AND status IN ('open', 'in_progress')
                ORDER BY id DESC
                LIMIT 1
                """
            ),
            {
                "control_id": control["id"],
                "title_prefix": f"Remediate {result.control_code}:%",
            },
        ).mappings().first()
        if existing:
            return int(existing["id"])

        created_at = datetime.now(timezone.utc).isoformat()
        owner_id = control.get("owner_user_id")
        returning = " RETURNING id" if self.db_session.bind.dialect.name == "postgresql" else ""
        cursor = self.db_session.execute(
            text(
                f"""
                INSERT INTO tasks (
                    type, source_object_type, source_object_id, control_id, check_id,
                    title, description, owner_id, assigned_to, status, priority,
                    created_at, updated_at
                )
                VALUES (
                    'remediation', 'control_check', :source_object_id, :control_id, :check_id,
                    :title, :description, :owner_id, :assigned_to, 'open', :priority,
                    :created_at, :updated_at
                )
                {returning}
                """
            ),
            {
                "source_object_id": check_id,
                "control_id": control["id"],
                "check_id": check_id,
                "title": f"Remediate {result.control_code}: {result.summary}",
                "description": result.remediation_steps or "Investigate the failed compliance check.",
                "owner_id": owner_id,
                "assigned_to": owner_id,
                "priority": "high" if result.status == CheckStatus.FAIL else "medium",
                "created_at": created_at,
                "updated_at": created_at,
            },
        )
        if self.db_session.bind.dialect.name == "postgresql":
            return int(cursor.scalar_one())
        inserted_id = cursor.lastrowid
        if inserted_id is not None:
            return int(inserted_id)
        row = self.db_session.execute(text("SELECT last_insert_rowid() AS id")).mappings().one()
        return int(row["id"])


async def run_all_automated_checks(db_session: Session) -> list[CheckResult]:
    return await CheckRunner(db_session).run_all(triggered_by="scheduler")
