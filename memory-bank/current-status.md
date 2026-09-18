# Current Status

## Date

2026-09-10

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

## Active Conventions

1. Public UI path: `uis/website`.
2. Internal UI path: `uis/backoffice`.
3. Backend services path: `services/`.

## Next Recommended Steps

1. Add persistent result storage for production API deployments.
2. Add monorepo-level scripts for lint/test/build per interface/service.
3. Expand skill catalog for PR review and architecture decision logging.

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
