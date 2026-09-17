# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

> _Spanish version: [README.es.md](./README.es.md)._

## Incident analyzer

The Brasaland incident analyzer is implemented in `incident_analysis.py` and exposed through `analyze.py`:

```bash
PYTHONPATH=scripts python3 scripts/analyze.py incidents-brasaland.csv
```

It validates the exact locations, categories, statuses and satisfaction rules from `CONTEXT.md`, prints the breakdown, and optionally writes `results.csv` with `metric`, `value` and `percentage` columns.
