from __future__ import annotations

from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load .env from the project root regardless of the working directory
load_dotenv(Path(__file__).parent.parent / ".env")

from app.db import init_db
from app.jobs import evidence_monitor
from app.routes import (
    audit_log,
    audits,
    auth,
    controls,
    dashboard,
    evidence,
    graph,
    integrations,
    jobs,
    sharepoint,
    tasks,
    workspaces,
)
from app.seed import seed_default_framework_and_controls


app = FastAPI(
    title="JEC SOC2 Readiness API",
    version="0.3.0",
    description="Internal SOC 2 Type 1/Type 2 readiness tracker for Jean Edwards Consulting.",
)

_scheduler: BackgroundScheduler | None = None
FRONTEND_DIR = Path("frontend")
BRANDING_DIR = Path("branding")


@app.on_event("startup")
def startup() -> None:
    global _scheduler
    init_db()
    seed_default_framework_and_controls()

    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone="UTC")
        _scheduler.add_job(evidence_monitor.run, "interval", hours=1, id="evidence-health")
        _scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/branding", StaticFiles(directory=BRANDING_DIR), name="branding")
app.include_router(auth.router)
app.include_router(controls.router)
app.include_router(evidence.router)
app.include_router(graph.router)
app.include_router(audits.router)
app.include_router(audit_log.router)
app.include_router(tasks.router)
app.include_router(dashboard.router)
app.include_router(jobs.router)
app.include_router(integrations.router)
app.include_router(sharepoint.router)
app.include_router(workspaces.router)
