# Admin API

Servicio HTTP ligero para las APIs operativas de Brasaland.

## Purpose

Centralize internal endpoints for operations, procurement, HR, and executive reporting.

## Monorepo Convention

This service exists under `services/` to comply with the repository backend placement rule.

## Incident analysis

Start the service from the repository root:

```bash
python3 services/admin-api/server.py --port 8000
```

The service exposes:

- `POST /api/incidents/analyze`: accepts a CSV file as `multipart/form-data` and returns the analysis as JSON.
- `GET /api/incidents/results/export`: downloads the latest analysis as `results.csv`.

The validation logic lives in `scripts/incident_analysis.py` and is shared by the CLI and API.

## Next Steps

1. Define API contract for store metrics and supplier pricing history.
2. Add a persistent result store for multi-process deployments.
3. Add integration tests to the service pipeline.
