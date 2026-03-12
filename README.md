# JEC SOC 2 Readiness MVP

This is a backend-first MVP for a Vanta-like internal platform for Jean Edwards Consulting (JEC).

It provides:
- SOC 2 control tracking
- Evidence artifact tracking for Type 1 and Type 2 windows
- Readiness scoring and gap reporting
- Phase 1 Vanta-style dashboard overview
- OneDrive-first evidence sync

## Stack

- Python 3.11+
- FastAPI
- SQLite
- APScheduler

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the API:

```bash
python -m uvicorn app.main:app --reload --port 8080
```

4. Open docs/UI:

- http://localhost:8080/docs
- http://localhost:8080/

## Core Endpoints

- `GET /health`
- `GET /controls`
- `POST /controls`
- `PATCH /controls/{control_db_id}/status`
- `GET /evidence`
- `POST /evidence`
- `POST /evidence/upload`
- `GET /dashboard/readiness`
- `GET /dashboard/gaps`
- `GET /dashboard/overview`
- `POST /jobs/run-evidence-check`
- `GET /integrations/status`
- `GET /integrations/runs`
- `POST /integrations/sync`

## OneDrive Environment Variables

Primary names:
- `ONEDRIVE_ACCESS_TOKEN`
- `ONEDRIVE_SITE_ID`
- `ONEDRIVE_DRIVE_ID`

Backward-compatible names (also accepted):
- `SHAREPOINT_ACCESS_TOKEN`
- `SHAREPOINT_SITE_ID`
- `SHAREPOINT_DRIVE_ID`

## Notes

- This app helps prepare for SOC 2; it does not claim certification.
- Keep auditor-facing evidence in a secured document store; this MVP stores only metadata and paths.
