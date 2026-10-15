# `brasaland-api`

FastAPI backend implementing authentication and route protection for the Brasaland platform (ticket **AUTH-01**). Built following the modular monolith structure proposed in [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md).

## Stack

- **FastAPI** + **Uvicorn**
- **TinyDB** — storage for `User` and `Profile` records.
- **Supabase/PostgreSQL via PostgREST** — persistent RFP tickets, metadata, and department sections; telemetry and reporting retain their existing adapters.
- **python-jose** — JWT signing/decoding.
- **libpass[bcrypt]** — password hashing (drop-in fork of `passlib`, imported as `from passlib.hash import bcrypt`).
- **uv** — dependency and project management.

## Structure

```text
src/brasaland_api/
├── main.py                 # FastAPI app, router registration
├── core/
│   ├── config.py           # Settings (.env-based)
│   ├── db.py                # TinyDB instance + table accessors
│   ├── security.py         # Password hashing + JWT helpers
│   └── deps.py              # get_current_user / require_admin dependencies
└── modules/
    ├── auth/                # Login, reset/change password, current user
    ├── agent/               # Manager support, RAG/MCP orchestration, approved episodic memory
    ├── users/                # /users CRUD (credentials only)
    ├── profiles/             # /profiles/me (display name + contact data)
    ├── incidents/            # /api/incidents ticket lifecycle (JWT protected)
    ├── operations/           # /operations/sales, /operations/inventory (protected)
    ├── supply_chain/         # /supply-chain/suppliers, /supply-chain/purchase-orders (protected)
    ├── telemetry/            # POST /telemetry/events (temporary batch receiver)
    └── hr/                   # /hr/employees (protected)
```

`operations`, `supply_chain`, and `hr` are minimal stub endpoints (in-memory data) that exist to prove that pre-existing sensitive routes outside `/users` and `/auth` are now guarded by `get_current_user`. The Incidents Manager remains TinyDB-backed. RFP ticket data is separate and stored in Supabase/PostgreSQL; its graph lives in `data/pipelines/rfp_intake/` rather than in the router.

## Setup

```bash
cd services/brasaland-api
cp .env.example .env   # then replace SECRET_KEY with your own value
uv sync
```

## Run

```bash
uv run uvicorn brasaland_api.main:app --app-dir src --reload --port 8000
```

Interactive docs: http://127.0.0.1:8010/docs

## Auth flow

1. `POST /users` — register (email, password, optional `name`/`phone`/`address` for the initial profile). Public.
2. `POST /auth/login` — form-encoded `username`/`password`, returns a JWT `access_token`.
3. Send `Authorization: Bearer <token>` on subsequent requests to any protected route.
4. `GET /auth/me` — returns the authenticated user's `email`, `role`, and linked `Profile`.
5. `POST /auth/forgot-password` sends a short-lived reset link through Resend and always returns a generic confirmation.
6. `POST /auth/reset-password` accepts a reset token once; `POST /auth/change-password` requires the current session token.

Unauthenticated requests to protected routes return `401`. Requests to a resource that belongs to another user (e.g. updating another user's credentials without an admin role) return `403`.

Authenticated manager-agent requests keep approved episodic memory private to the JWT subject. `GET /agent/memory` reads approved notes and `GET /agent/memory/audit` reads proposal/decision history; both are read-only. Memory writes happen only after explicit approval or a safe explicit edit in the agent conversation.

The manager-support agent's input, output, and external-content guardrails are documented in [`docs/agent-memory/guardrail-harness.md`](../../docs/agent-memory/guardrail-harness.md). The authenticated `GET /agent/guardrails/summary` endpoint reports this process's guardrail block/redirect counters for the current manager.

## Environment variables

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | JWT signing key. Must be set in `.env`, never hardcoded. |
| `JWT_ALGORITHM` | Signing algorithm (default `HS256`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes. |
| `TINYDB_PATH` | Path to the TinyDB JSON file (default `data/db.json`). |
| `AGENT_MEMORY_DB_PATH` | SQLite file for per-user approved agent notes and proposal audit; defaults to `~/.local/state/brasaland/agent_memory.sqlite3`. Set to a durable volume in deployment. |
| `SUPABASE_URL` | Supabase project URL used by the telemetry batch writer. |
| `SUPABASE_SERVICE_ROLE_KEY` | Secret server-side key used only by FastAPI; never expose it to the browser or commit it. |
| `CORS_ORIGINS` | Comma-separated allow-list of browser origins permitted to call this API (default `http://localhost:3000,http://127.0.0.1:3000`, for the Next.js dev frontend). |

## Telemetry storage

Apply `migrations/001_create_telemetry_events.sql` to the Supabase project before enabling ingestion. It creates the append-only table, the timestamp/event-type/JSONB indexes, and insert-only access for `service_role`. Configure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the API's local `.env` or deployment secret store. The receiver validates events individually and sends all accepted rows in one PostgREST request. `tags` contains exactly the validated event `properties`; envelope IDs are not duplicated there.

`GET /telemetry/report` is a technical report for event volume, error rate, API latency, and daily authentication failures. It reads `telemetry_events` through read-only PostgREST queries, applies a 7-day UTC window by default, and caches each period for 60 seconds. Run its isolated tests with `PYTHONPATH=src:../.. uv run pytest tests/test_telemetry_analysis.py -q`. A live report requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`; the endpoint returns a generic 503 while they are unset.

Analysis uses Pandas and remains separate from the weekly business pipeline in `services/reporting/`; it only selects `timestamp`, `event_type`, `level`, `value`, and `tags` from `telemetry_events` and never writes to that table.
| `CORS_ORIGINS` | Comma-separated allow-list of browser origins permitted to call this API (default `http://localhost:3000,http://127.0.0.1:3000`, for the Next.js dev frontend). |
| `TELEMETRY_ENDPOINT` | Configured telemetry receiver URL (default `http://localhost:8000/telemetry/events`; reserved for the next pipeline phase). |
| `CORS_ORIGINS` | Comma-separated allow-list of browser origins permitted to call this API (default `http://localhost:3000,http://127.0.0.1:3000`, for the Next.js dev frontend). |
| `RESEND_API_KEY` | Resend API key used to deliver password-reset emails. Required for delivery; never commit the value. |
| `RESEND_FROM_EMAIL` | Verified sender address configured in Resend (default `onboarding@resend.dev` for testing). |
| `FRONTEND_BASE_URL` | Base URL used to build reset links (default `http://localhost:3000`). |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | Reset token lifetime, restricted to 15–60 minutes (default `30`). |

Run the API unit tests from this directory with `PYTHONPATH=src python -m unittest discover -s tests`.

## RFP Ticket Intake

Apply `migrations/003_create_rfp_intake.sql` to the Supabase project before enabling the RFP endpoints. The migration creates `public.rfp_tickets`, `public.rfp_metadata`, and `public.department_sections`, with service-role access. The API uses the existing `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` settings; configure them only in the backend environment.

`POST /rfp-intake` accepts one PDF (maximum 25 MB), writes the artifact to repository `data/raw/rfp-intake/`, creates an `analizando` ticket, and returns `202` with `ticket_id`. FastAPI `BackgroundTasks` then invokes the dedicated LangGraph under `data/pipelines/rfp_intake/`. `GET /rfp-intake` lists recent tickets and `GET /rfp-intake/{ticket_id}` returns status, metadata, department sections, processing error, and synthesizer handoff. All routes require JWT authentication.

The PDF is converted with MarkItDown before classification. Readability uses `py-readability-metrics` when tokenizer resources are available and a deterministic local estimate otherwise. A failed background run records `processing_error` and does not falsely complete the ticket. The in-process task is not a durable queue, so production deployments requiring restart recovery should replace dispatch with a durable worker while retaining this API and graph contract.

Focused RFP API and pipeline tests:

```bash
PYTHONPATH=src:../.. uv run pytest --import-mode=importlib tests/test_rfp_intake.py ../../tests/pipelines/test_rfp_intake.py -q
```
