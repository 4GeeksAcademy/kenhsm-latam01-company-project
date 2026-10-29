# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

## Convention for this repository

Any new backend component must be created under `services/<service-name>/`.

Suggested first service types:

1. `admin-api/` for centralized operational endpoints.
2. `telemetry-worker/` for data ingestion and processing.

Current service entrypoints:

1. `api/` exposes the incident analysis API required by the project delivery.
2. `brasaland-api/` is the central FastAPI backend with JWT authentication, `users`/`profiles` (TinyDB-only), and route protection (AUTH-01).
3. `brasaland-api/` also exposes the centralized incident lifecycle at `/api/incidents` and persists incident records in TinyDB.
4. `reporting/` contains authenticated business KPI endpoints backed by Prefect flows in `data/pipelines/`, plus the independent `job_runner.py` state store for nightly telemetry export; both remain separate from technical telemetry analysis.
5. `brasaland-api/` exposes the authenticated RFP ticket flow at `/rfp-intake`; its LangGraph is owned by `data/pipelines/rfp_intake/` and persists to Supabase/PostgreSQL.
5. `brasaland-api/` exposes the authenticated RFP ticket flow at `/rfp-intake`; its LangGraph is owned by `data/pipelines/rfp_intake/` and persists to Supabase/PostgreSQL.

> _Spanish version: [README.es.md](./README.es.md)._
