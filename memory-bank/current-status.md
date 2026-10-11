# Current Status

## Date

2026-09-27
2026-09-10

2026-09-26
## Completed

1. Created repository-level agent operating protocol in `AGENTS.md`.
2. Created coding-agent configuration scaffold in `.agents/`.
3. Added initial memory bank files with business and technical context.
4. Established initial reusable agent skill with explicit acceptance criteria.
5. Added first visible UI entrypoints in `uis/website` and `uis/backoffice`.
6. Added the reusable Brasaland incident analyzer, CLI export, admin API endpoints and backoffice upload view.
7. Added the `services/api` delivery entrypoint, delegating to the shared admin API implementation without duplicating analysis logic.
8. Added `services/brasaland-api` (FastAPI + TinyDB + uv): JWT auth (`/auth/login`, `/auth/me`), `users` CRUD (`/users`), `profiles` (`/profiles/me`), and `get_current_user`/`require_admin` dependencies applied to all non-public routes, including 5 stub sensitive routes in `operations`, `supply_chain`, and `hr` modules (AUTH-01).
9. Added frontend auth flows to `apps/talent-pipeline-tracker` (protected app, developer-authorized edit): `/login`, `/register`, `/account` pages, a client-side `AuthGuard` protecting every route except `/login`/`/register`, and header login/logout controls — all backed by `services/brasaland-api` via `services/auth.ts` (AUTH-02).
10. Applied the caching audit: Next.js interactive panels use `next/dynamic`, the candidate filtering uses dependency-scoped `useMemo`, and FastAPI has observable timing plus per-user TTL caches for sales and employees with employee-write invalidation. Decisions are documented in `CACHING_REPORT.md`.
10. Added centralized incident management to `services/brasaland-api` (`/api/incidents` CRUD, lifecycle transitions, filters, summary) with TinyDB persistence, shared validation in `packages/shared`, and an idempotent `scripts/seed_incidents.py`.
11. Extended `uis/backoffice` with incident registration, filters, status updates, loading/error/empty states, and summary metrics.



## Active Conventions

1. Public UI path: `uis/website`.
2. Internal UI path: `uis/backoffice`.
3. Backend services path: `services/`.

## Next Recommended Steps

1. Add persistent result storage for production API deployments.
2. Add monorepo-level scripts for lint/test/build per interface/service.
3. Expand skill catalog for PR review and architecture decision logging.

## Telemetry Plan Decision

The telemetry design lives in `docs/telemetry/telemetry-plan.md` and `docs/telemetry/event-schemas.json`. The registry covers six context-mandated inventory events plus opportunities across inventory validation, authentication, access, navigation, API health, incident analysis, purchasing, accounts, and background jobs. Current operations/inventory routes are stubs; only existing auth, purchase-request, user-account, and incident-analysis flows are candidates for immediate capture. Domain inventory events remain future instrumentation until persistent traceable orders exist. Event payloads are allowlisted, user identifiers are pseudonymized, and money remains in the location currency.

## Incident Analysis Decision

The CLI and API share `scripts/incident_analysis.py` so validation and metrics remain identical across terminal and backoffice workflows. The API currently keeps the latest result in memory, which is suitable for local use and should be replaced by durable storage before multi-process deployment.

## AUTH-01 Decision

`User` and `Profile` are stored exclusively in TinyDB (`services/brasaland-api/data/db.json`, gitignored) and will remain so even after Supabase/PostgreSQL is introduced for other modules — other tables must reference the TinyDB user id as `user_uuid`. Auth is stateless JWT only (no sessions/cookies), signed with `python-jose`, passwords hashed with `libpass[bcrypt]` (`from passlib.hash import bcrypt`). The `operations`, `supply_chain`, and `hr` modules currently contain minimal in-memory stub routes only to demonstrate protection of pre-existing sensitive endpoints per the architecture proposal; they need real persistence in a later ticket.

## AUTH-02 Decision

The JWT is stored in `localStorage` (key `brasaland_access_token`) and attached as `Authorization: Bearer <token>` on every call to `services/brasaland-api`. Route protection is client-side only (`app/components/auth-guard.tsx`, using `useSyncExternalStore` over localStorage to avoid the `react-hooks/set-state-in-effect` lint rule) — no Next.js Proxy/middleware is used, per the ticket's constraint that it cannot read `localStorage`. `NEXT_PUBLIC_AUTH_API_URL` configures the backend base URL (defaults to `http://127.0.0.1:8010`). `uis/website` (public site) and `uis/backoffice` (static HTML, not Next.js) are out of scope for this ticket; only `apps/talent-pipeline-tracker` was updated, with explicit developer authorization since it is a protected area per `AGENTS.md`.

Account management lives at `/account/profile` (not `/account`). `lib/auth-fetch.ts` provides `authenticatedFetch`: attaches the token automatically and, on any `401` from a protected call, clears the token and throws `UnauthorizedError` — `AuthGuard` reacts to the cleared token (via the shared `useStoredToken` store) and redirects to `/login` without any page needing manual redirect logic. `services/auth.ts` exposes `AuthApiError` (with `status` + backend `detail`) so `/register` can show field-level errors (e.g. duplicate email from `POST /users` → 400) and `/login` shows the backend's actual message.

**Bugs found and fixed while verifying AUTH-02 end-to-end with Playwright (real browser, not just curl):**
1. `services/brasaland-api` had no CORS middleware, so every browser call from the Next.js app (different port/origin) was silently blocked. Fixed by adding `CORSMiddleware` with an allow-list (`CORS_ORIGINS` env var, defaults to `http://localhost:3000,http://127.0.0.1:3000`).
2. `AuthGuard` redirected authenticated users to `/login` on a **hard reload** of a protected route: `useSyncExternalStore`'s first client render after hydration briefly reports the SSR snapshot (`null`), and the redirect effect fired on that stale value before the hook resynced. Fixed by re-checking `getStoredToken()` directly inside the redirect effect instead of trusting the transient hook value for the decision (the hook value is still used for the render-time content gate).
3. Local dev testing must use `http://localhost:3000`, not `http://127.0.0.1:3000` — Next.js Turbopack dev blocks cross-origin HMR websocket requests from `127.0.0.1` by default, which breaks client-side interactivity in that origin during `next dev`.

## Telemetry Storage Decision

Added per-event validation for `POST /telemetry/events`, a property allowlist matching the approved registry, and one bulk PostgREST insert per non-empty valid batch. The migration creates `telemetry_events`, the three analytical indexes, and insert-only privileges for `service_role`; rows store only validated `properties` in `tags`. This branch has no Supabase URL/service-role credentials, so the migration has not been applied remotely and live persistence remains pending local/deployment configuration. The frontend was not changed.



## Business Pipeline Design Decision

Added `data/pipelines/PIPELINE_DESIGN.md` for the weekly Brasaland location cost and waste report. The design specifies the five business KPIs, Prefect flow/tasks, the `reporting.weekly_location_performance` grain, run auditing, retry/recovery, late-event recalculation, and the separate planned `services/reporting/` endpoints. It also records verified implementation gaps: current telemetry persistence drops `eventId`/`requestId`, inserts without deduplication, and this checkout has no `GET /telemetry/report` implementation despite the milestone brief describing one. No orchestration, reporting tables, or reporting API were implemented in this design phase.

Added required nonnegative `unit_cost` to the existing `stock_waste_registered` event schema, receiver allowlist, and backoffice emitter so waste cost can be computed as quantity times unit cost. The client drops missing, negative, and non-finite costs. Purchase cost continues to use the existing `quantity` and `unit_price`. Monetary values remain in each location's currency.

## Business Reporting Pipeline Implementation

Implemented the weekly Prefect flow in `data/pipelines/pipeline.py`, with pure weekly KPI transformation, idempotent upsert by `(location_id, week_start)`, structured run metadata, one-hour transformation caching, retry policies, and a non-critical evaluation snapshot. Added authenticated reporting endpoints and the `reporting` schema migration; the admin-only manual endpoint invokes the same flow as the CLI.

The CLI was verified in local validation mode without Supabase credentials. Production deployment still requires the migration and PostgREST exposure of `reporting`. Existing telemetry persistence does not retain the envelope `eventId`; the pipeline defensively deduplicates by the persisted row `id` and does not change the telemetry writer. The source also has no explicit per-location completeness signal, so zero-filled locations must be interpreted with that limitation.

The backoffice now has a weekly business report page at `uis/backoffice/reporting.html`, using the authenticated reporting API and showing all five weekly location KPIs. The requested Milestone 3 Prefect subflow refactor and `tests/pipelines/test_pipeline.py` are still pending: the editor's Copilot content exclusion rejects reads and edits under `data/`, and this task did not bypass that restriction.

`uv add` could not resolve the existing `services/brasaland-api/uv.lock` because it contains duplicate `certifi` package records; Prefect is declared in `pyproject.toml` and installed in the active environment, but the lock still needs regeneration.

## Sales Forecast Decision (2026-10-11)

Added a reproducible Random Forest sales-forecast pipeline with causal lag/rolling/calendar features, recursive 2024-2025 evaluation, a tree-spread variability band, and documented MSE, PSI, low-month Gini, and explicitly defined seasonal-naive K2 skill metrics. The requested `data/raw/brasaland_sales.csv` is absent from this checkout, so the real model, metrics, and visualization cannot be generated until that source file is provided; no replacement data was simulated.

Added a separate time-aware model evaluation with five expanding 12-month folds, fold-local causal feature construction, recursive validation forecasts, MAE/RMSE summaries, learning-curve generation, and evidence-based fit diagnosis/action recommendations. The split/order and validation-label invariance tests pass. Since the original sales CSV is still missing, no real fold results, learning-curve image, or fit classification can be asserted yet; `data/eval/evaluation_report.md` records this limitation and the evaluation command will populate measured outputs when the source arrives.

## LangGraph Agent Decision (2026-10-11)

Added the explicit LangGraph-based Brasaland assistant flow with a minimal `AgentState` (question, context, answer, trace, error), conditional routing, and `MemorySaver` checkpointing. The graph reuses the existing knowledge pipeline via `retrieve()` and `generate_answer(question, context)` without wrapping the monolithic `query()` function. Every run logs a structured trace of node execution order, and the service exposes it through `POST /agent/query` with a clean error payload instead of a raw stack trace.

The focused validation suite in `tests/pipelines/test_langgraph_agent.py` checks the trace order, the honest no-context route, and answer anchoring to recovered RAG context. The regression tests for the existing knowledge pipeline still pass, and the route smoke test verifies the final API contract.

## Brasaland MCP Decision (2026-10-11)

Added `mcps/brasaland` as an independent Streamable HTTP MCP server. It uses `mcpauth` as an OAuth/OIDC resource server (JWT issuer, JWKS, audience, global `mcp:access`, and per-tool scopes), publishes Protected Resource Metadata, and documents schemas, scopes, and error behavior. Incident tools call the registered JWT-protected Incidents Manager API; status changes use only `/api/incidents/{id}/status`. Inventory has a read tool and an explicit write-denial tool which never calls the API.

The LangGraph tool branch discovers/invokes tools through `langchain-mcp-adapters`; regular questions retain the existing RAG branch. MCP-server and service dependencies are declared in their respective uv projects, with the adapter also present in the root environment used by graph tests. Focused MCP, agent, and incidents API tests pass. Hosted MCP Playground testing is pending deployment-time OAuth issuer/client provisioning and public port forwarding; no provider credentials were available in this workspace.

## AUTH-03 Decision

Password-reset JWTs use a dedicated `purpose` claim and a random `jti`; only the SHA-256 hash of that ID and its expiration are persisted in TinyDB. The 30-minute default is configurable only within 15–60 minutes. Consuming a token updates the password and removes its persisted record under a process-local lock, preventing reuse. Reset emails are delivered through Resend using `RESEND_API_KEY` and `RESEND_FROM_EMAIL`; `/auth/forgot-password` returns the same confirmation for known and unknown addresses and suppresses delivery failures from the response. The frontend reset routes are public; `/account/change-password` remains behind `AuthGuard`.

## Agent Memory Decision (2026-10-11)

Extended the existing manager-support LangGraph with authenticated, owner-scoped episodic SQLite memory outside the source tree and outside Qdrant `brasaland_knowledge`. Memory is explicit: load approved notes, resolve one pending proposal before normal RAG/MCP routing, then persist only an approved or safe-edited proposal. A single structured model completion supplies the answer and optional proposal. User decisions, source message, confidence, status, and timestamps are auditable through the `memory_proposals` table and authenticated `/agent/memory/audit`; `/agent/memory` exposes the manager's approved notes read-only.

Privacy controls block customer/Brasa Points and payroll/compensation data from facts, scope, reasons, and source messages. A JWT-derived owner ID scopes each note; the prompt treats notes as unverified and subordinate to company RAG. Explicit bilingual decision classification fails closed on ambiguity/contradiction. Pending proposals expire after 7 days; facts after 180 days; resolved audit records after 730 days. Facts consolidate by owner/category/scope and are capped at 50 per owner, with only 8 loaded per turn. The default SQLite file is `~/.local/state/brasaland/agent_memory.sqlite3`; deployment must set `AGENT_MEMORY_DB_PATH` to durable storage.

Approval, rejection, edit, ambiguity, non-memorable examples, privacy, expiry, caps, and owner-isolated API reads are covered in `services/brasaland-api/tests/test_agent_memory.py` and `test_agent_memory_flow.py`. The OIDC/MCP Playground prerequisite from the prior milestone remains unrelated and still requires deployment credentials.

## Agent Guardrail Harness Decision (2026-10-11)

Secured the same `manager_support` graph with a deterministic input gate before memory/RAG/MCP, a short bilingual small-talk/trivia redirect path, and validated generation/tool outputs. The system policy is fixed in the system role and explicitly limits the agent to Brasaland manager operations; user input, approved memory, RAG documents, and MCP results are sanitized/escaped and isolated as untrusted data. Exact recipe formulas, supplier prices/contracts, payroll/performance data, and customer identifiers are blocked at input/output boundaries. Malformed structured output falls back to validated RAG excerpts without a model retry; extra model fields fail structural validation.

Guardrail activation is logged with session, category, action, and count; authenticated `GET /agent/guardrails/summary` exposes process-local counters. Deterministic abuse and output-isolation tests live in `services/brasaland-api/tests/test_agent_guardrails.py`; required jailbreak variants and three-turn recipe extraction are documented in `docs/agent-memory/guardrail-harness.md`. Cross-worker production metrics still need a shared telemetry backend before being treated as global totals.

## Documentation Consolidation Decision (2026-10-11)

Created `docs/brasaland/contexto-maestro.md` and `docs/brasaland/especificaciones-maestro.md` as canonical company context and consolidated milestone requirements. Updated `AGENTS.md`, root `README.md`, and `docs/README.md` to direct contributors there; telemetry plan links now point at the canonical context. Removed 11 unprotected root `CONTEXT*.md` duplicates and 17 root `SPECS*.md` files after incorporating their domain contracts and acceptance criteria. The protected root `CONTEXT.md` and `context-company.md`, plus `.agents/SPECSTELEMETRYREPORT.md`, remain unchanged. Historical source filenames are retained in the specifications provenance matrix.


