# Reporting Service

The `/reporting` routes serve the weekly Brasaland business KPIs and manually trigger the Prefect flow in `data/pipelines/`. They are registered in the authenticated `services/brasaland-api` application and remain separate from technical telemetry.

## Endpoints

- `GET /reporting/pipeline-runs/latest` returns run status and execution metadata.
- `POST /reporting/pipeline-runs` queues a manual run; administrators may pass a Monday `week_start` query parameter.
- `GET /reporting/weekly-location-performance` returns the latest published week, or a requested Monday via `week_start`.

Production runs require `SUPABASE_URL`, `SUPABASE_REPORTING_READ_KEY`, and `SUPABASE_REPORTING_WRITE_KEY`. The existing `SUPABASE_SERVICE_ROLE_KEY` remains a development fallback. The flow issues only GET requests against `telemetry_events`; report writes target the `reporting` schema.

Apply `services/brasaland-api/migrations/002_create_reporting_schema.sql` and expose the `reporting` schema in Supabase PostgREST before production use. The intended reporting cycle is weekly on Monday at 06:00 `America/Bogota`.

Run the CLI from the repository root with `python data/pipelines/pipeline.py`. When Supabase credentials are absent, it reads `data/raw/telemetry_events.json` and writes local validation artifacts under `data/eval`; this mode does not publish business KPIs.