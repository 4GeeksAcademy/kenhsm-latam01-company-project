# Incident Analysis API

Entry point required by the incident analyzer delivery structure. It delegates to the shared implementation in `services/admin-api/server.py`.

Run from the repository root:

```bash
python3 services/api/server.py --port 8000
```

The API exposes `POST /api/incidents/analyze` and `GET /api/incidents/results/export`.
