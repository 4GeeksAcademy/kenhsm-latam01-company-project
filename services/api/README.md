# Brasaland APIs

This directory contains FastAPI applications for Brasaland.

## Supplier Directory API

A lightweight API for managing the Brasaland supplier directory using FastAPI + TinyDB.

### Setup

```bash
cd services/api
uv sync
```

### Run the API

```bash
cd services/api
uv run fastapi dev main.py
```

The API will be available at `http://localhost:8000`.

### Seed the database

```bash
cd services/api
uv run python seed.py
```

This loads all initial supplier data from the briefing into TinyDB.

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints

- `POST /suppliers` - Create a new supplier
- `GET /suppliers` - List all suppliers (supports `?country=X` and `?category=Y` filters)
- `GET /suppliers/{id}` - Get supplier details
- `PATCH /suppliers/{id}/rate` - Update supplier rate
- `PATCH /suppliers/{id}/status` - Update supplier status (active/suspended)
- `DELETE /suppliers/{id}` - Delete a supplier

---

## Incident Analysis API (Legacy)

Entry point required by the incident analyzer delivery structure. It delegates to the shared implementation in `services/admin-api/server.py`.

Run from the repository root:

```bash
python3 services/api/server.py --port 8000
```

The API exposes `POST /api/incidents/analyze` and `GET /api/incidents/results/export`.
