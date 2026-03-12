from __future__ import annotations

from app import repository


def run() -> dict:
    return repository.run_evidence_health_check()

