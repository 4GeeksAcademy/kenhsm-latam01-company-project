# Progress

## Estado actual

1. Existe `AGENTS.md` en raiz con flujo obligatorio pre-commit y orden de lectura.
2. Existe `.agents/` con reglas activas y una skill reutilizable (`pr-readiness-check`).
3. Existe `memory-bank/` con contexto de negocio, tecnico, reglas y estado operativo.
4. Existen interfaces iniciales visibles en `uis/website` y `uis/backoffice`.
5. Existe `services/brasaland-api` (FastAPI + TinyDB + uv) con autenticacion JWT, CRUD de `users`, `profiles`, y proteccion de rutas sensibles (AUTH-01).

## Proximos pasos previstos

1. Crear el primer servicio backend en `services/` (por ejemplo, `admin-api/` o `telemetry-worker/`). — done via `services/brasaland-api`.
2. Definir scripts de validacion por area (lint, type-check, test, build) para estandarizar verificacion pre-PR.
3. Expandir catalogo de skills de agente para tareas recurrentes (por ejemplo, decision log updater, release notes generator).
4. Conectar progresivamente las UIs con servicios reales y datos operativos.
5. Reemplazar los stubs en memoria de `operations`, `supply_chain` y `hr` con persistencia real (Supabase/PostgreSQL) y actualizar el frontend para enviar el JWT.
