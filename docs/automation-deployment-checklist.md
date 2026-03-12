# Automation Deployment Checklist (JEC SOC2 MVP)

Use this to enable low-touch operations safely.

## Prerequisites

- Codex runtime supports automation registry (`automations` table and TOML configs).
- Dedicated service account with least-privilege access to:
  - Git provider
  - Cloud provider logs/config
  - Ticketing system
  - Document repository
- Secrets manager configured for API keys and rotation.

## Required Automation Jobs

1. Evidence freshness monitor (hourly)
- Trigger `POST /jobs/run-evidence-check`.
- Open ticket when controls are flagged.

2. Daily readiness snapshot (daily)
- Call `GET /dashboard/readiness`.
- Persist JSON snapshot for trend analysis.

3. Weekly gap digest (weekly)
- Call `GET /dashboard/gaps`.
- Send report to compliance channel and owner list.

4. Monthly auditor packet prep (monthly)
- Gather accepted evidence metadata from `GET /evidence`.
- Produce CSV/JSON export by control and period.

## Guardrails

- All automation runs must be idempotent.
- Set retry policy with exponential backoff.
- Enforce per-job timeout and max attempts.
- Log run id, actor id, timestamp, and output hash.
- Never auto-close compliance tickets without explicit owner approval.

## Go-Live Gates

- 14-day dry run with no critical automation failures.
- 100% of failed runs produce actionable error messages.
- Manual override documented and tested.
- Auditor accepts packet format and naming standards.
