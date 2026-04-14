from __future__ import annotations

import logging
from typing import Dict, List, Type, Optional

from app.services.checks.base import BaseCheck, CheckResult

logger = logging.getLogger(__name__)

class Registry:
    def __init__(self):
        self._checks: Dict[str, BaseCheck] = {}

    def register(self, check: BaseCheck):
        """Register a check instance for its control_id."""
        if check.control_id in self._checks:
            logger.warning(f"Overwriting check for control {check.control_id}")
        self._checks[check.control_id] = check
        logger.info(f"Registered check '{check.name}' for control {check.control_id}")

    def get_check(self, control_id: str) -> Optional[BaseCheck]:
        return self._checks.get(control_id)

    def list_controls(self) -> List[str]:
        return list(self._checks.keys())

    async def run_check(self, control_id: str, **kwargs) -> Optional[CheckResult]:
        check = self.get_check(control_id)
        if not check:
            logger.error(f"No automated check registered for control {control_id}")
            return None
        return await check.run(**kwargs)

# Global registry instance
check_registry = Registry()
