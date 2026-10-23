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

## RFP Ticket Intake

Open `http://localhost:3000/rfp-intake.html`. The page reuses the authenticated API token at `brasaland_access_token` and includes the existing login flow if no token is present. `NEXT_PUBLIC_RFP_API_ENDPOINT` in `.env.local` may set the API base URL; otherwise it uses `NEXT_PUBLIC_REPORTING_API_ENDPOINT` or `http://127.0.0.1:8000`.

PDFs are sent to `POST /rfp-intake` on the existing `services/brasaland-api`; the endpoint saves them under `data/raw/rfp-intake/`, creates an `analizando` ticket, and starts the `data/pipelines/rfp_intake/` graph in a background task. Marketing starts Part 2 from the completed analysis; rejected tickets in `needs_human_review` can explicitly reopen generation. The ticket then shows drafts, evaluations, approval state, fixed-arbitrator conflicts, and ordered execution trace. The named department owner can approve, reject, or request changes; Operations/Procurement can enter structured event terms and all department owners can enter setup lead time. The API verifies the signed-in profile name. The final document appears only after all required approvals.

Before enabling the full flow, apply `services/brasaland-api/migrations/003_create_rfp_intake.sql` and `services/brasaland-api/migrations/004_create_rfp_approvals.sql` to Supabase and ensure the API's server-side `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` can access the `public` tables. Set `RFP_CHECKPOINT_PATH` to a durable-volume path. The service-role key must never be placed in `.env.local`.

### Live RFP notifications

The page consumes authenticated `GET /rfp-intake/events` with `fetch` and the `brasaland_access_token` bearer token. The named `rfp_ticket_created` event carries `ticket_id`, `rfp_id`, `client_name`, `location`, `service_type`, `status`, and `created_at`. It is published only after the classifier accepts the document as a valid RFP and its metadata is persisted. The payload uses `status: "analyzing"` from the real-time contract while the existing RFP workflow continues to persist its initial status as `analizando`. The stream sends comment keep-alives every 15 seconds and retries with exponential backoff, capped at 30 seconds.

Recovery uses the existing ticket list, filtered from the latest known `created_at` and paged in batches of 50 on every connection/reconnection. SSE events received during reconciliation and list results are deduplicated by `ticket_id`. A normal event updates the visible queue and notification without refetching the list; the list is refetched only when establishing/re-establishing the stream.

Each dashboard tab has an independent stream and subscriber queue. Fifty clients therefore mean fifty long-lived HTTP connections and queues; the current broker is process-local and does not fan out across multiple API workers/instances. A multi-worker deployment should replace it with shared fan-out such as Redis Pub/Sub or PostgreSQL notifications. SSE fits this one-way server-to-dashboard notification; user actions remain ordinary authenticated HTTP requests. If users need bidirectional messages over the same live channel, WebSockets become appropriate.

Manual recovery check: sign in to the dashboard in one browser, confirm the live connection status, then switch that browser's network to offline in DevTools. Submit one or more PDFs from a second connected session, restore the first browser's network, and confirm the interrupted/retry status changes back to connected, the missing tickets appear, and each `ticket_id` appears only once. In the Network panel, confirm the event stream uses `Authorization: Bearer ...` and that ordinary ticket events do not trigger repeated list requests.

## Manager Support Chat

Open `http://localhost:3000/manager-chat.html`. The page reuses `brasaland_access_token` and `NEXT_PUBLIC_REPORTING_API_ENDPOINT` (default `http://127.0.0.1:8000`). Select a Brasaland `location_id`; the socket is `/agent/chat/{session_id}?token=...&location_id=...`. The server resolves that token with the same `get_current_user` JWT dependency as the API. Use HTTPS/WSS outside local development and redact query strings containing `token` from proxy/access logs.

`ChatSession` records `session_id`, `agent_id=manager_support`, JWT-derived `user_id`, `location_id`, `status`, and `created_at`. Messages and event sequence are stored in SQLite at `CHAT_SESSION_DB_PATH` (default `~/.local/state/brasaland/chat_sessions.sqlite3`). The browser retains the same session and location in `sessionStorage`; each connection restores messages from `session_snapshot` and drops duplicate queued events using `event_sequence`. The stored history is passed to the existing graph with `session_id` as its `thread_id`.

The async graph stream publishes `token_chunk` events while the model is producing its structured answer. `interrupt_requested` cancels the producer task and closes the in-flight AsyncOpenAI stream; it is separate from LangGraph HITL `interrupt()`, which is not used here. The partial assistant message remains in history with `status=interrupted`; the correction is a new user message and a new assistant message. A per-session in-memory pub/sub channel fans one producer's events out to every subscribed socket, so additional viewers do not call the agent again. This broker and generation lock are process-local; multi-worker deployments need shared pub/sub and distributed generation ownership.

### Manual Chat Verification

1. Start the API with `uv run uvicorn brasaland_api.main:app --app-dir src --reload --port 8000` from `services/brasaland-api`, and serve `uis/backoffice` over HTTP.
2. Sign in at `manager-chat.html`, select a location, ask a question that takes long enough to stream, then send a correction while tokens are arriving. Confirm the original bubble retains its partial text and is marked `Interrumpido`, followed by a separate response that uses the correction.
3. While connected, switch the browser offline and back online. Confirm the page reconnects with the same `session_id`, displays stored history from `session_snapshot`, and does not duplicate messages or tokens.
4. `services/brasaland-api/tests/test_agent_chat.py` verifies named event payloads, JWT rejection, subscriber fan-out, and that cancelling the original generation produces no further chunks for that message.

WebSockets are required because the user must send `interrupt_requested` while the agent is streaming; the Part 1 SSE channel only carries server-to-client events. The producer publishes once per `chat.<session_id>` channel and all subscribed sockets consume that same event stream. Abort cancels model generation rather than pausing the graph; the interrupted assistant message is retained and redirected input starts a new turn.
