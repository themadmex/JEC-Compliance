from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import inspect, text


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import engine


FRAMEWORK_NAME = "SOC 2"
FRAMEWORK_VERSION = "2017 TSC"


@dataclass(frozen=True)
class SeedControl:
    code: str
    title: str
    category: str
    automated: str
    frequency: str
    evidence_requirements: str


SEED_CONTROLS = [
    SeedControl(
        "CC6.1",
        "MFA Enforcement",
        "Logical and Physical Access Controls",
        "yes",
        "continuous",
        "Evidence that MFA is enforced for all in-scope users and exceptions are tracked.",
    ),
    SeedControl(
        "CC6.2",
        "Access Provisioning",
        "Logical and Physical Access Controls",
        "partial",
        "monthly",
        "Access request approvals, role assignments, and monthly provisioning review records.",
    ),
    SeedControl(
        "CC6.3",
        "Access Revocation / Deprovisioning",
        "Logical and Physical Access Controls",
        "yes",
        "continuous",
        "Terminated-user deprovisioning logs and disabled-account evidence.",
    ),
    SeedControl(
        "CC6.6",
        "Least Privilege / Privileged Access Review",
        "Logical and Physical Access Controls",
        "partial",
        "quarterly",
        "Privileged access review exports, reviewer sign-off, and remediation evidence.",
    ),
    SeedControl(
        "CC7.1",
        "Vulnerability Detection",
        "System Operations",
        "yes",
        "daily",
        "Vulnerability scan results, triage notes, and remediation tracking.",
    ),
    SeedControl(
        "CC7.2",
        "Security Monitoring / Incident Detection",
        "System Operations",
        "yes",
        "continuous",
        "Monitoring alerts, incident review records, and alert coverage evidence.",
    ),
    SeedControl(
        "CC8.1",
        "Change Management",
        "Change Management",
        "partial",
        "on_change",
        "Approved pull requests, testing evidence, deployment logs, and rollback notes.",
    ),
    SeedControl(
        "CC9.1",
        "Risk Assessment",
        "Risk Mitigation",
        "no",
        "annual",
        "Annual risk assessment, risk register, mitigation owners, and leadership approval.",
    ),
    SeedControl(
        "A1.1",
        "Backup Verification",
        "Availability",
        "yes",
        "daily",
        "Backup job history, restore test results, and backup failure remediation records.",
    ),
    SeedControl(
        "P1.1",
        "Privacy Notice",
        "Privacy",
        "no",
        "annual",
        "Current privacy notice, approval history, and evidence that notice is published.",
    ),
]


def _columns(conn, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(conn).get_columns(table_name)}


def _ensure_framework(conn) -> int:
    framework_columns = _columns(conn, "frameworks")
    if "description" in framework_columns:
        conn.execute(
            text(
                """
                INSERT INTO frameworks (name, version, description)
                VALUES (:name, :version, :description)
                ON CONFLICT(name, version) DO NOTHING
                """
            ),
            {
                "name": FRAMEWORK_NAME,
                "version": FRAMEWORK_VERSION,
                "description": "SOC 2 Trust Services Criteria",
            },
        )
    else:
        conn.execute(
            text(
                """
                INSERT INTO frameworks (name, version)
                VALUES (:name, :version)
                ON CONFLICT(name, version) DO NOTHING
                """
            ),
            {"name": FRAMEWORK_NAME, "version": FRAMEWORK_VERSION},
        )
    row = conn.execute(
        text(
            """
            SELECT id FROM frameworks
            WHERE name = :name AND version = :version
            """
        ),
        {"name": FRAMEWORK_NAME, "version": FRAMEWORK_VERSION},
    ).mappings().one()
    return int(row["id"])


def _automation_flag(value: str) -> int:
    return 1 if value in {"yes", "partial"} else 0


def seed_controls() -> int:
    with engine.begin() as conn:
        framework_id = _ensure_framework(conn)
        control_columns = _columns(conn, "controls")
        phase1_schema = "control_code" in control_columns

        for control in SEED_CONTROLS:
            if phase1_schema:
                conn.execute(
                    text(
                        """
                        INSERT INTO controls (
                            framework_id, control_id, control_code, title, description,
                            category, owner, frequency, is_automated, implementation_status,
                            type1_ready, type2_ready, type1_status, type2_status,
                            evidence_requirements
                        )
                        VALUES (
                            :framework_id, :control_id, :control_code, :title, :description,
                            :category, :owner, :frequency, :is_automated, :implementation_status,
                            :type1_ready, :type2_ready, :type1_status, :type2_status,
                            :evidence_requirements
                        )
                        ON CONFLICT(framework_id, control_id) DO NOTHING
                        """
                    ),
                    {
                        "framework_id": framework_id,
                        "control_id": control.code,
                        "control_code": control.code,
                        "title": control.title,
                        "description": control.evidence_requirements,
                        "category": control.category,
                        "owner": "Compliance Lead",
                        "frequency": control.frequency,
                        "is_automated": _automation_flag(control.automated),
                        "implementation_status": "draft",
                        "type1_ready": 0,
                        "type2_ready": 0,
                        "type1_status": "not_started",
                        "type2_status": "not_started",
                        "evidence_requirements": control.evidence_requirements,
                    },
                )
                conn.execute(
                    text(
                        """
                        UPDATE controls
                        SET title = :title, description = :description,
                            category = :category, frequency = :frequency,
                            is_automated = :is_automated,
                            type1_status = 'not_started',
                            type2_status = 'not_started',
                            evidence_requirements = :evidence_requirements,
                            control_code = :control_code
                        WHERE framework_id = :framework_id AND control_id = :control_id
                        """
                    ),
                    {
                        "title": control.title,
                        "description": control.evidence_requirements,
                        "category": control.category,
                        "frequency": control.frequency,
                        "is_automated": _automation_flag(control.automated),
                        "evidence_requirements": control.evidence_requirements,
                        "control_code": control.code,
                        "framework_id": framework_id,
                        "control_id": control.code,
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO controls (
                            framework_id, control_id, title, description, owner,
                            implementation_status, type1_ready, type2_ready
                        )
                        VALUES (
                            :framework_id, :control_id, :title, :description, :owner,
                            :implementation_status, :type1_ready, :type2_ready
                        )
                        ON CONFLICT(framework_id, control_id) DO NOTHING
                        """
                    ),
                    {
                        "framework_id": framework_id,
                        "control_id": control.code,
                        "title": control.title,
                        "description": control.evidence_requirements,
                        "owner": "Compliance Lead",
                        "implementation_status": "draft",
                        "type1_ready": 0,
                        "type2_ready": 0,
                    },
                )

        return len(SEED_CONTROLS)


def main() -> None:
    count = seed_controls()
    print(f"Seeded {count} SOC 2 starter controls.")


if __name__ == "__main__":
    main()
