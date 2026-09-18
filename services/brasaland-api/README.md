# `brasaland-api`

FastAPI backend implementing authentication and route protection for the Brasaland platform (ticket **AUTH-01**). Built following the modular monolith structure proposed in [`docs/ARCHITECTURE_PROPOSAL.md`](../../docs/ARCHITECTURE_PROPOSAL.md).

## Stack

- **FastAPI** + **Uvicorn**
- **TinyDB** — the only storage for `User` and `Profile` records (now and after any future Supabase/PostgreSQL integration for other domains).
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
    ├── auth/                # POST /auth/login, GET /auth/me
    ├── users/                # /users CRUD (credentials only)
    ├── profiles/             # /profiles/me (display name + contact data)
    ├── operations/           # /operations/sales, /operations/inventory (protected)
    ├── supply_chain/         # /supply-chain/suppliers, /supply-chain/purchase-orders (protected)
    └── hr/                   # /hr/employees (protected)
```

`operations`, `supply_chain`, and `hr` are minimal stub endpoints (in-memory data) that exist to prove that pre-existing sensitive routes outside `/users` and `/auth` are now guarded by `get_current_user`. They will be replaced by their full implementations (with Postgres/Supabase persistence) in later tickets.

## Setup

```bash
cd services/brasaland-api
cp .env.example .env   # then replace SECRET_KEY with your own value
uv sync
```

## Run

```bash
uv run uvicorn brasaland_api.main:app --app-dir src --reload --port 8010
```

Interactive docs: http://127.0.0.1:8010/docs

## Auth flow

1. `POST /users` — register (email, password, optional `name`/`phone`/`address` for the initial profile). Public.
2. `POST /auth/login` — form-encoded `username`/`password`, returns a JWT `access_token`.
3. Send `Authorization: Bearer <token>` on subsequent requests to any protected route.
4. `GET /auth/me` — returns the authenticated user's `email`, `role`, and linked `Profile`.

Unauthenticated requests to protected routes return `401`. Requests to a resource that belongs to another user (e.g. updating another user's credentials without an admin role) return `403`.

## Environment variables

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | JWT signing key. Must be set in `.env`, never hardcoded. |
| `JWT_ALGORITHM` | Signing algorithm (default `HS256`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes. |
| `TINYDB_PATH` | Path to the TinyDB JSON file (default `data/db.json`). |
| `CORS_ORIGINS` | Comma-separated allow-list of browser origins permitted to call this API (default `http://localhost:3000,http://127.0.0.1:3000`, for the Next.js dev frontend). |
