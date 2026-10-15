# RFP Intake Pipeline

The `rfp_intake` package owns the RFP intake graph; the existing FastAPI router only persists the uploaded ticket, launches the graph as a background task, and serves ticket state.

## Flow

1. MarkItDown converts the uploaded PDF to Markdown before the classifier sees document content.
2. The classifier accepts actionable service requests with identifiable scope and a contractual, budget, or deadline commitment. Formal RFPs and informal requests are accepted; a franchise inquiry without actionable scope is discarded.
3. Metadata extraction records client, location, service type, scope, deadline, budget, missing fields, word count, estimated input tokens, and readability measures.
4. The orchestrator routes only to `marketing`, `operaciones`, `procurement`, and `training`. Workers receive shared metadata and relevant source extracts; they do not estimate missing figures.
5. The synthesizer stores department aspects and contacts in the ticket handoff payload for Part 2.

Marketing / Camila Ospina is always included as ticket owner. `training` is only added for co-branding, author/custom-menu, or new-recipe signals; standard-menu catering does not route there.

Unknown departments are not converted into ad-hoc workers. They and conflicting quantities remain in `open_questions` for Marketing to route or confirm. Workers preserve source text rather than negotiate contradictory numbers. Background failures keep the allowed status `analizando`, set `processing_error`, and appear in the UI as requiring re-receipt; they never become `analisis_completo` silently.

## Local Checks

```bash
cd services/brasaland-api
PYTHONPATH=src:../.. uv run pytest --import-mode=importlib tests/test_rfp_intake.py ../../tests/pipelines/test_rfp_intake.py -q
```

The sample PDFs referenced in `CONTEXT-companyH91.md` are not present in this checkout. Tests cover the three described request profiles; upload verification with the original PDFs remains pending their availability.