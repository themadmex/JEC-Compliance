from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class CheckResult:
    control_code: str
    check_name: str
    status: CheckStatus
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    run_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    remediation_steps: str | None = None


class BaseCheck(ABC):
    """Base class for all automated compliance checks."""

    def __init__(self, name: str, control_code: str, description: str):
        self.name = name
        self.control_code = control_code
        self.description = description

    @property
    def check_name(self) -> str:
        return self.name.lower().replace(" ", "_").replace("/", "_")

    def result(
        self,
        status: CheckStatus,
        summary: str,
        details: dict[str, Any] | None = None,
        remediation_steps: str | None = None,
    ) -> CheckResult:
        return CheckResult(
            control_code=self.control_code,
            check_name=self.check_name,
            status=status,
            summary=summary,
            details=details or {},
            remediation_steps=remediation_steps,
        )

    @abstractmethod
    async def run(self, **kwargs) -> CheckResult:
        """Execute the check logic."""
