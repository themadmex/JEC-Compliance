from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy.orm import Session

from app.services.integrations.base import IntegrationBase, IntegrationRunResult

logger = logging.getLogger(__name__)

_TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

_FIXTURE_DATA: dict[str, Any] = {
    "iam_users": [
        {"user_id": "AIDA000000000000001", "username": "admin-user", "admin": True},
        {"user_id": "AIDA000000000000002", "username": "readonly-user", "admin": False},
    ],
    "cloudwatch_alarms": [
        {"alarm_name": "HighErrorRate", "state": "OK"},
        {"alarm_name": "UnauthorizedAPICalls", "state": "OK"},
    ],
    "backup_jobs": [
        {"job_id": "bkp-001", "status": "COMPLETED", "resource_type": "RDS"},
    ],
    "s3_buckets": [
        {"name": "jec-compliance-evidence", "encryption": "AES256"},
    ],
}


def _assume_role_session() -> Any:
    import boto3

    role_arn = os.environ["AWS_ROLE_ARN"]
    sts = boto3.client("sts")
    creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="JECComplianceSync")[
        "Credentials"
    ]
    import boto3

    session = boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )
    return session


def _fetch_iam_admin_users(session: Any) -> list[dict[str, Any]]:
    iam = session.client("iam")
    users: list[dict[str, Any]] = []
    paginator = iam.get_paginator("list_users")
    for page in paginator.paginate():
        for user in page["Users"]:
            policies = iam.list_attached_user_policies(UserName=user["UserName"])[
                "AttachedPolicies"
            ]
            admin = any(p["PolicyName"] in ("AdministratorAccess", "PowerUserAccess") for p in policies)
            users.append({"user_id": user["UserId"], "username": user["UserName"], "admin": admin})
    return users


def _fetch_cloudwatch_alarms(session: Any) -> list[dict[str, Any]]:
    cw = session.client("cloudwatch")
    alarms: list[dict[str, Any]] = []
    paginator = cw.get_paginator("describe_alarms")
    for page in paginator.paginate():
        for alarm in page["MetricAlarms"]:
            alarms.append({"alarm_name": alarm["AlarmName"], "state": alarm["StateValue"]})
    return alarms


def _fetch_backup_jobs(session: Any) -> list[dict[str, Any]]:
    backup = session.client("backup")
    jobs: list[dict[str, Any]] = []
    paginator = backup.get_paginator("list_backup_jobs")
    for page in paginator.paginate(ByState="COMPLETED"):
        for job in page["BackupJobs"][:50]:  # cap at 50 most recent
            jobs.append(
                {
                    "job_id": job["BackupJobId"],
                    "status": job["State"],
                    "resource_type": job.get("ResourceType", ""),
                }
            )
    return jobs


def _fetch_s3_encryption(session: Any) -> list[dict[str, Any]]:
    s3 = session.client("s3")
    buckets: list[dict[str, Any]] = []
    for bucket in s3.list_buckets().get("Buckets", []):
        name = bucket["Name"]
        try:
            enc = s3.get_bucket_encryption(Bucket=name)
            rules = enc["ServerSideEncryptionConfiguration"]["Rules"]
            algo = rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] if rules else "none"
        except Exception:
            algo = "none"
        buckets.append({"name": name, "encryption": algo})
    return buckets


class AWSIntegration(IntegrationBase):
    name = "aws"

    def health_check(self) -> bool:
        if _TEST_MODE:
            return True
        try:
            _assume_role_session()
            return True
        except Exception:
            return False

    def sync(self, db: Session) -> IntegrationRunResult:
        run = self._start_run(db)
        try:
            if _TEST_MODE:
                iam_users = _FIXTURE_DATA["iam_users"]
                cw_alarms = _FIXTURE_DATA["cloudwatch_alarms"]
                backup_jobs = _FIXTURE_DATA["backup_jobs"]
                s3_buckets = _FIXTURE_DATA["s3_buckets"]
            else:
                session = _assume_role_session()
                iam_users = _fetch_iam_admin_users(session)
                cw_alarms = _fetch_cloudwatch_alarms(session)
                backup_jobs = _fetch_backup_jobs(session)
                s3_buckets = _fetch_s3_encryption(session)

            snapshots: list[dict[str, Any]] = []
            for u in iam_users:
                snapshots.append(
                    {"resource_type": "iam_user", "resource_id": u["user_id"], "data": u}
                )
            for alarm in cw_alarms:
                snapshots.append(
                    {
                        "resource_type": "cloudwatch_alarm",
                        "resource_id": alarm["alarm_name"],
                        "data": alarm,
                    }
                )
            for job in backup_jobs:
                snapshots.append(
                    {"resource_type": "backup_job", "resource_id": job["job_id"], "data": job}
                )
            for bucket in s3_buckets:
                snapshots.append(
                    {"resource_type": "s3_bucket", "resource_id": bucket["name"], "data": bucket}
                )

            count = self._write_snapshots(db, run, snapshots)
            result = IntegrationRunResult(
                integration_name=self.name, status="success", records_synced=count
            )
        except Exception as exc:
            logger.exception("AWS sync failed")
            result = IntegrationRunResult(
                integration_name=self.name, status="failed", error_message=str(exc)
            )

        self._finish_run(db, run, result)
        db.commit()
        return result
