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
