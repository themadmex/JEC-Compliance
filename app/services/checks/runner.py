from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app import db
from app.services.checks.registry import check_registry
from app.services.checks.mfa import GoogleMFACheck
from app.services.checks.github import GitHubVulnerabilityCheck, GitHubBranchProtectionCheck
from app.services.checks.aws import AWSAdminAccessCheck, ABACAccessCheck

logger = logging.getLogger(__name__)

def initialize_engine():
    """Register all available checks in the global registry."""
    check_registry.register(GoogleMFACheck())
    check_registry.register(GitHubVulnerabilityCheck())
    check_registry.register(GitHubBranchProtectionCheck())
    check_registry.register(AWSAdminAccessCheck())
    check_registry.register(ABACAccessCheck())
    # Add more checks here as they are implemented
    logger.info("Compliance Check Engine initialized.")


async def run_all_automated_checks(db_session: Session):
    """Execution loop for all registered automated checks."""
    controls = check_registry.list_controls()
    logger.info(f"Starting execution of {len(controls)} automated checks...")
    
    for control_id in controls:
        result = await check_registry.run_check(control_id)
        if result:
            # 1. Log to control_checks table
            # We fetch the control numeric ID from the database first
            from app.services.controls_service import get_control_by_id
            control_record = get_control_by_id(control_id) # Note: This handles the lookup
            
            if not control_record:
                logger.error(f"Cannot log check result: Control {control_id} not found in DB.")
                continue
                
            # 2. Persist result
            db_session.execute(
                db.text("""
                    INSERT INTO control_checks (control_id, checked_at, result, details)
                    VALUES (:control_id, :checked_at, :result, :details)
                """),
                {
                    "control_id": control_record["id"],
                    "checked_at": result.checked_at.isoformat(),
                    "result": result.status.value,
                    "details": json.dumps(result.details)
                }
            )
            
            # 3. Update control status (Type I readiness)
            # If the check passes, we consider it Type 1 ready (snapshot passing)
            is_ready = 1 if result.status == "pass" else 0
            db_session.execute(
                db.text("""
                    UPDATE controls 
                    SET type1_ready = :is_ready, last_tested_at = :tested_at
                    WHERE id = :control_id
                """),
                {
                    "is_ready": is_ready,
                    "tested_at": result.checked_at.isoformat(),
                    "control_id": control_record["id"]
                }
            )
            
            # 4. Auto-generate evidence (Phase 2 Requirement)
            if result.status == "pass":
                from app.services.evidence_service import create_evidence
                from app.schemas import EvidenceCreate
                
                create_evidence(EvidenceCreate(
                    control_id=control_record["id"],
                    name=f"Automated Check - {result.control_id}",
                    source="check-engine",
                    artifact_path=f"engine://{result.control_id}/{result.checked_at.strftime('%Y-%m-%d')}",
                    collected_at=result.checked_at,
                    status="accepted",
                    notes=json.dumps(result.details)
                ))
            
            # 5. Automated Remediation Tasks (Phase 3 Requirement)
            if result.status in ["fail", "error"]:
                from app.services.task_service import create_task
                from app.schemas import TaskCreate
                
                # Assign to control owner if possible, fallback to IT Operations (ID 1)
                owner_id = 1 
                
                create_task(TaskCreate(
                    type="remediation",
                    source_object_type="control_check",
                    source_object_id=control_record["id"],
                    title=f"Remediate {result.control_id}: {result.summary}",
                    description=f"Action required: {result.remediation_steps or 'Investigate compliance failure.'}\n\nDetails: {json.dumps(result.details)}",
                    owner_id=owner_id,
                    priority="high" if result.status == "fail" else "medium"
                ))

    db_session.commit()
    logger.info("Automated check execution cycle completed.")
