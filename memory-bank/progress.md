# Progress

## Estado actual

1. Existe `AGENTS.md` en raiz con flujo obligatorio pre-commit y orden de lectura.
2. Existe `.agents/` con reglas activas y una skill reutilizable (`pr-readiness-check`).
3. Existe `memory-bank/` con contexto de negocio, tecnico, reglas y estado operativo.
4. Existen interfaces iniciales visibles en `uis/website` y `uis/backoffice`.
5. Existe `services/brasaland-api` (FastAPI + TinyDB + uv) con autenticacion JWT, CRUD de `users`, `profiles`, y proteccion de rutas sensibles (AUTH-01).
6. AUTH-03 implementado en backend y frontend: recuperacion por email con Resend, tokens persistidos de un solo uso, y cambio autenticado de contraseña; suite backend y build/lint frontend verificados.
7. Implemented the weekly Prefect business KPI pipeline, reporting schema migration, and JWT-protected reporting endpoints; local CLI and focused data/API tests pass. Production Supabase configuration and telemetry-source completeness remain deployment prerequisites.
8. Added the explicit LangGraph agent flow for Brasaland knowledge retrieval with conditional routing, checkpointing, structured trace logging, and a `/agent/query` API endpoint. The graph reuses the existing RAG retrieval and generation functions while keeping the routing logic inspectable and testable.
9. Added the OAuth-protected Brasaland Streamable HTTP MCP server under `mcps/brasaland`, with ticket lifecycle tools, read-only inventory, explicit write denial, discovery metadata, and structured invocation logs. Registered/protected the Incidents Manager API and routed LangGraph incident actions through `langchain-mcp-adapters`; focused MCP, API, and agent checks pass. Remote MCP Playground validation remains pending an externally configured OIDC issuer/client and public port forwarding.
10. Extended the same manager-support LangGraph with per-user SQLite episodic memory, structured answer/proposal output, explicit bilingual consent classification, audited approval/rejection/edit/ambiguity, owner-scoped read/audit APIs, deterministic non-memorable filters, expiry, deduplication, and per-user caps. Focused memory-cycle, privacy, endpoint, and RAG/MCP regression suites pass for Hito 8 Part 1.
11. Added the Hito 8 Part 2 harness to the same manager-support agent: pre-routing jailbreak/scope/content checks, brief bilingual small-talk/trivia redirects, untrusted RAG/MCP isolation, strict structured-output and secret-leak validation, authenticated session counters, and deterministic tests for five contextual jailbreak variants plus three-turn recipe extraction. Focused RAG/MCP, memory, guardrail, and API tests pass.
12. Consolidated Brasaland context and milestone requirements into `docs/brasaland/contexto-maestro.md` and `docs/brasaland/especificaciones-maestro.md`; updated `AGENTS.md`/README links and retired 28 unprotected root duplicates. Kept the protected context files and `.agents` telemetry-report specification unchanged.

## Proximos pasos previstos

1. Crear el primer servicio backend en `services/` (por ejemplo, `admin-api/` o `telemetry-worker/`). — done via `services/brasaland-api`.
2. Definir scripts de validacion por area (lint, type-check, test, build) para estandarizar verificacion pre-PR.
3. Expandir catalogo de skills de agente para tareas recurrentes (por ejemplo, decision log updater, release notes generator).
4. Conectar progresivamente las UIs con servicios reales y datos operativos.
5. Reemplazar los stubs en memoria de `operations`, `supply_chain` y `hr` con persistencia real (Supabase/PostgreSQL) y actualizar el frontend para enviar el JWT.
