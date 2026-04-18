from __future__ import annotations

import logging

from app.services.checks.base import BaseCheck, CheckResult

logger = logging.getLogger(__name__)


class CheckRegistry:
    def __init__(self):
        self._checks: dict[str, BaseCheck] = {}

    def register(self, check: BaseCheck) -> None:
        """Register a check instance for its control code."""
        if check.control_code in self._checks:
            logger.warning("Overwriting check for control %s", check.control_code)
        self._checks[check.control_code] = check
        logger.info("Registered check '%s' for control %s", check.name, check.control_code)

    def get_check(self, control_code: str) -> BaseCheck | None:
        return self._checks.get(control_code)

    def list_controls(self) -> list[str]:
        return list(self._checks.keys())

    def list_checks(self) -> list[BaseCheck]:
        return list(self._checks.values())

    async def run_check(self, control_code: str, **kwargs) -> CheckResult | None:
        check = self.get_check(control_code)
        if not check:
            logger.error("No automated check registered for control %s", control_code)
            return None
        return await check.run(**kwargs)


check_registry = CheckRegistry()
