from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.integrations import IntegrationRun, IntegrationSnapshot

logger = logging.getLogger(__name__)


@dataclass
class IntegrationRunResult:
    integration_name: str
    status: str  # success | partial | failed
    records_synced: int = 0
    error_message: str | None = None
    snapshots: list[dict[str, Any]] = field(default_factory=list)


class IntegrationBase(ABC):
    name: str

    def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def sync(self, db: Session) -> IntegrationRunResult:
        """Pull data, write integration_runs + integration_snapshots rows."""

    def _start_run(self, db: Session) -> IntegrationRun:
        started_at = datetime.now(timezone.utc)
        run = IntegrationRun(
            source=self.name,
            integration_name=self.name,
            started_at=started_at,
            finished_at=started_at,
            status="in_progress",
            details="{}",
            records_synced=0,
        )
        db.add(run)
        db.flush()
        return run

    def _finish_run(self, db: Session, run: IntegrationRun, result: IntegrationRunResult) -> None:
        run.status = result.status
        run.finished_at = datetime.now(timezone.utc)
        run.records_synced = result.records_synced
        run.error_message = result.error_message
        run.details = json.dumps(
            {
                "integration_name": result.integration_name,
                "status": result.status,
                "records_synced": result.records_synced,
                "error_message": result.error_message,
            }
        )
        db.flush()

    def _write_snapshots(
        self,
        db: Session,
        run: IntegrationRun,
        snapshots: list[dict[str, Any]],
    ) -> int:
        count = 0
        for snap in snapshots:
            row = IntegrationSnapshot(
                run_id=run.id,
                source=self.name,
                snapshot_type=snap.get("resource_type"),
                data_json=json.dumps(snap.get("data", {})),
                integration_name=self.name,
                resource_type=snap.get("resource_type"),
                resource_id=snap.get("resource_id"),
                data=json.dumps(snap.get("data", {})),
                captured_at=datetime.now(timezone.utc),
            )
            db.add(row)
            count += 1
        db.flush()
        return count
