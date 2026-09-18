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
