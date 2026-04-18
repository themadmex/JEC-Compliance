# Phase 2 Prep - Check Engine

This repo is ready to start PRD v2.3 Phase 2 after the remaining Phase 1 acceptance checks are kept green.

## Build Rules

- Keep new routes under `/api/v1/`; preserve old route aliases until the frontend moves.
- Do not use random or simulated check results in production paths.
- Use `TEST_MODE=true` for deterministic fixtures in local tests and CI.
- Every check run must write a `control_checks` row, including failures and errors.
- Auditors may see `result_summary`; they must never receive `result_detail`.

## First Implementation Targets

1. Replace the current enum/string mismatch in `app/services/checks/runner.py`.
2. Introduce a deterministic fixture provider keyed by `TEST_MODE`.
3. Move check modules toward one module per seeded control:
   - `CC6.1` MFA enforcement
   - `CC6.2` access provisioning
   - `CC6.3` deprovisioning
   - `CC6.6` privileged access review
   - `CC7.1` vulnerability detection
   - `CC7.2` security monitoring
   - `CC8.1` change management
   - `A1.1` backup verification
   - `CC9.1` and `P1.1` manual guidance checks
4. Add tests that assert a passing fixture writes one check row and a failing fixture creates one open task.

## Phase 2 Entry Criteria

- `python -m unittest tests.test_phase1_foundation -v` passes.
- `alembic upgrade head` passes on clean SQLite.
- `python scripts/seed_controls.py` can be run repeatedly.
- `from app.main import app` imports successfully.
