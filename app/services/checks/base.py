from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warning"
    ERROR = "error"


@dataclass
class CheckResult:
    control_id: str
    status: CheckStatus
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    remediation_steps: Optional[str] = None


class BaseCheck:
    """Base class for all automated compliance checks."""
    
    def __init__(self, name: str, control_id: str, description: str):
        self.name = name
        self.control_id = control_id
        self.description = description

    async def run(self, **kwargs) -> CheckResult:
        """Execute the check logic. To be implemented by subclasses."""
        raise NotImplementedError("Each check must implement the run() method.")
