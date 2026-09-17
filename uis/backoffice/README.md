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

Open `index.html` in a browser.

For incident analysis, start the API with `python3 services/admin-api/server.py --port 8000` before uploading a CSV.
