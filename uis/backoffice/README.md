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

The telemetry receiver validates the envelope and logs each batch but does not persist events. Inventory-order, stock, and authentication UI flows are not implemented in this backoffice yet, so their events are accepted by the service contract but are not synthesized from unrelated actions.
