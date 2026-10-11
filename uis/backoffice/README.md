# Backoffice UI

Internal operations interface for Brasaland teams.

## Current Scope

1. Entry route `/` via `index.html` rendered by modular frontend files.
2. Own layout separated from the public website layout.
3. Reusable UI components in `components.js`.
4. Operational data fragment visible in UI from `data.js` aligned to `CONTEXT.md`.
5. Base layout to evolve into internal modules (operations, HR, procurement).
6. Incident analysis module with CSV upload, invalid-record breakdown and results download.

## Quick Start

The backoffice reads public endpoint settings from `.env.local`, so serve it over HTTP rather than opening `index.html` as a `file://` URL.

1. Start the telemetry receiver from `services/brasaland-api`:

	```bash
	uv run uvicorn brasaland_api.main:app --app-dir src --reload --port 8000
	```

2. Start the incident-analysis API on a separate port from the repository root:

	```bash
	python3 services/admin-api/server.py --port 8001
	```

3. Serve this directory from the repository root:

	```bash
	python3 -m http.server 3000 --directory uis/backoffice
	```

Open `http://localhost:3000`. `.env.local` contains only public endpoint URLs; never put secrets in it. Copy `telemetry.env.example` to `.env.local` when setting up another checkout.

The telemetry receiver validates envelopes and persists accepted batches to Supabase when configured; without Supabase credentials it returns a safe service-unavailable response. Inventory-order and stock UI flows are not implemented in this backoffice yet, so their events are not synthesized from unrelated actions.

## Weekly business report

Open `http://localhost:3000/reporting.html` for the weekly location cost and waste dashboard. It signs in through `/auth/login` and reads `/reporting/weekly-location-performance` from `services/brasaland-api`; the API base URL is `NEXT_PUBLIC_REPORTING_API_ENDPOINT` in `.env.local` (default `http://127.0.0.1:8000`). Use a Brasaland account with permission to read reporting data. The JWT is stored under the existing `brasaland_access_token` local-storage key and is shared with the other authenticated Brasaland UI.

## Technical Telemetry Dashboard

Open `http://localhost:3000/telemetry.html`. It reads `GET /telemetry/report` from `services/brasaland-api`; `NEXT_PUBLIC_TELEMETRY_REPORT_ENDPOINT` in `.env.local` sets the API URL (default `http://127.0.0.1:8000/telemetry/report`). The page supports optional UTC start/end date-times and shows event volume, error rate, API latency, and login failure rate. Configure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the backend service's private `.env` to populate it; without them the API returns a safe unavailable state. Never put these server credentials in the UI's `.env.local`.
