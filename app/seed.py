from __future__ import annotations

from app.db import get_connection


SEED_CONTROLS = [
    (
        "CC1.1",
        "Control Environment Oversight",
        "Management establishes security governance and accountability.",
        "Security Lead",
        "implemented",
        1,
        0,
    ),
    (
        "CC2.1",
        "Risk Assessment Process",
        "Identify, analyze, and prioritize internal and external security risks.",
        "Compliance Lead",
        "implemented",
        1,
        0,
    ),
    (
        "CC6.1",
        "Logical Access Controls",
        "Restrict system access to authorized users and enforce least privilege.",
        "IT Operations",
        "implemented",
        1,
        0,
    ),
    (
        "CC7.2",
        "Security Monitoring",
        "Monitor systems for anomalies and respond to incidents in defined timelines.",
        "Security Operations",
        "draft",
        0,
        0,
    ),
    (
        "CC8.1",
        "Change Management",
        "Track and approve production changes with testing and rollback plans.",
        "Engineering Manager",
        "draft",
        0,
        0,
    ),
]


def seed_default_framework_and_controls() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO frameworks (name, version)
            VALUES ('SOC 2', '2017 TSC')
            """
        )
        framework_id = int(
            conn.execute(
                """
                SELECT id FROM frameworks WHERE name = 'SOC 2' AND version = '2017 TSC'
                """
            ).fetchone()["id"]
        )

        for control in SEED_CONTROLS:
            conn.execute(
                """
                INSERT OR IGNORE INTO controls (
                    framework_id, control_id, title, description, owner,
                    implementation_status, type1_ready, type2_ready
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (framework_id, *control),
            )

