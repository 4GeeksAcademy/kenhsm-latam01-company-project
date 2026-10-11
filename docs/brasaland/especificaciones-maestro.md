# Especificaciones Maestras de Brasaland

**Registro canónico de requisitos del proyecto.** Los nombres históricos de los documentos fuente se conservan en la matriz de procedencia; los criterios de este archivo son la versión consolidada para trabajo futuro. El contexto de empresa, modelos y políticas está en [contexto-maestro.md](./contexto-maestro.md). Los documentos técnicos que son entregables implementados (diseño RAG, plan de telemetría, diseño de memoria, harness, reportes) permanecen en `docs/` y se enlazan desde aquí o desde `docs/README.md`.

> Este documento consolida requisitos y criterios de aceptación, no certifica por sí mismo que cada hito esté completo. El estado de implementación y la evidencia de pruebas se mantiene en `memory-bank/current-status.md` y `memory-bank/progress.md`.

## Invariantes compartidas

- Respetar el dominio y contratos de [contexto-maestro.md](./contexto-maestro.md): nombres de campos, IDs, categorías, estados, sedes, monedas, idiomas, eventos, KPIs y restricciones de privacidad.
- Reutilizar lógica de dominio existente; no duplicar ETL en routers ni reescribir RAG para agentes.
- No cambiar un área protegida por `AGENTS.md` sin autorización explícita. No versionar secretos.
- Las pruebas deterministas son el gate; una demo en vivo no las sustituye.
- El reporte técnico `GET /telemetry/report` y su origen `telemetry_events` permanecen independientes del reporting ejecutivo bajo `reporting`.

## 1. Entorno reproducible en Docker — `SPECSDOCKER.md`

Dockerizar el monorepo para desarrollo mediante `docker compose up`: un contenedor de UI sirve website y backoffice en puertos 3000/3001; un contenedor ejecuta FastAPI con reload. Ambos deben tener bind mounts, leer entorno desde `.env`, comunicarse por nombre de servicio dentro de una red Compose con nombre explícito, y arrancar sin pasos manuales adicionales. Incluir Dockerfiles y `.dockerignore` bajo `/uis` y `/services`. No incluir credenciales en Dockerfiles ni YAML; mantener `.env` ignorado.

## 2. Auditoría de rendimiento frontend — `SPECSAUDITF.md`

Medir Lighthouse antes/después en website y backoffice; guardar puntuaciones Performance, Accessibility, Best Practices y SEO, métricas relevantes y capturas en `audit/before/` y `audit/after/`. Revisar causas raíz, identificar al menos dos duplicaciones candidatas y extraer al menos un componente/hook reutilizable. Lazy-load al menos dos rutas/componentes y priorizar LCP/CLS/INP. Entregar `AUDIT.md` con diagnóstico inicial y `REPORT.md` con cambios/impacto medido. Evitar reescrituras de arquitectura y no perseguir 100 por sí mismo.

## 3. Pruebas de API de auth y backlog — `SPECSBULLET.md`

Crear `TESTING.md` con el plan **antes de los tests**: camino feliz, límite y fallo por endpoint; entradas como campos vacíos, duplicados, tokens malformados/expirados. Cubrir la lógica de negocio de registro, login, token/sesión, reset y cambio de contraseña con pytest, sin probar serialización/framework. Ejecutar `uv run pytest --cov`; objetivo de auth ≥70%. Si hay utilidades TS, Jest/coverage en ellas. Extras: dos grupos backoffice con ≥60% y al menos tres helpers frontend, ambos documentados. Registrar el caso límite/bug que reveló la batería.

## 4. Caché con evidencia — `SPECSCACHING.md`

Medir antes de optimizar. En el frontend, aplicar lazy loading a dos componentes/rutas justificados y `useMemo` solo a un cálculo no trivial con dependencias correctas. En FastAPI, medir coste/frecuencia/estabilidad y elegir al menos dos lecturas repetidas con TTL e invalidación cuando cambie el origen; claves privadas deben incluir identidad. `CACHING_REPORT.md` debe explicar coste, tráfico, frescura vs rendimiento, TTL, invalidación y al menos una operación deliberadamente no cacheada.

## 5. Procesamiento CSV de incidentes — `SPECSBULLET.md` / contexto raíz consolidado

El analizador CSV valida el esquema y valores de `contexto-maestro.md`, informa todos los tipos de error, calcula conteos válidos por categoría/estado y distribución/promedio de satisfacción, ofrece exportación CSV y tiene CLI. Para el fixture de 100 filas se esperan 96 válidas, cuatro inválidas (una por cada regla documentada), categorías 29/17/22/19/9, estados 32/50/14, satisfacción 4/6/12/19/9 y media 3.46. Mantener lógica reutilizable para que el gestor de incidencias pueda compartirla.

## 6. Gestor de incidencias — `SPECSINCIDENCIAS.md`

Modelo con ID, título, descripción, categoría, estado, origen, branch y timestamps; validaciones de dominio y ciclo de vida. Seed desde CSV transforma antes de insertar, usa `origin=customer`, descarta/reportea filas inválidas y es idempotente por ID fuente. API CRUD: crear, filtrar/listar, detalle, cambiar únicamente estado por transición y resumen por estado/categoría/origen/sede; lista vacía y resumen cero son válidos, error genérico no expone stack. Backoffice: formulario, filtros/listado, actualización de estado, summary, estados de carga/vacío/error/reintento y rollback visual ante fallo. Reutilizar validación de `packages/shared`.

## 7. Recuperación y cambio de contraseña — `SPECSPASSRESET.md`

`POST /auth/forgot-password` devuelve respuesta indistinguible exista o no el email y envía enlace cuando corresponde. Reset valida firma, expiración 15–60 min y uso único; almacena estado server-side para invalidación. Change-password requiere sesión y verifica la actual. Frontend: forgot/reset/cambio con confirmación de contraseña, token de query string, éxito/error claro, regreso a login y enlace desde login. Secretos Resend solo por entorno. Cubrir fail, expiración, reuso y enumeración.

## 8. Base RAG — `SPECSCONOCIMIENTO.md`

Indexar solo los cuatro documentos oficiales de Brasaland indicados en `contexto-maestro.md` a Qdrant `brasaland_knowledge`, con chunks semánticos y payload de fuente/sección/compañía/idioma/índice/texto. Funciones separadas `setup`, `embed`, `retrieve`, `generate_answer` y `query`; embedding dedicado distinto al LLM. Setup idempotente. Retrieval aplica top-k y score mínimo, puede devolver menos de k/cero. Generación responde desde contexto, honestamente sin él, fiel a idioma, alérgenos y moneda original. Endpoint `/knowledge/query` devuelve solo respuesta generada; UI maneja loading/error. Evals con ≥8 queries y Recall@3 ≥80%; tests mockean Qdrant/LLM y exigen no retornar chunks crudos. Mantener `docs/rag/rag-design.md`.

## 9. Telemetría de inventario — `SPECSTELEMETRY.md`

Primero diseño, luego instrumentación. Cubrir los seis eventos obligatorios de `contexto-maestro.md` y un catálogo amplio de oportunidades técnicas/operativas, cada uno con hipótesis y decisión. Definir envelope con ID, timestamp UTC, sesión, user pseudonimizado, event type, schema version, request correlation y properties; permitir solo propiedades allowlisted. Especificar stream/batch por urgencia, throttling/debounce, PII sanitizada, riesgos y exclusiones. Entregar `docs/telemetry/telemetry-plan.md` y `event-schemas.json` validable.

## 10. Reporte técnico de telemetría — `.agents/SPECSTELEMETRYREPORT.md`

Construir ≥3 análisis técnicos independientes en Pandas desde Supabase: volumen por día/tipo, error rate y latencia/auth si los eventos existen. Filtrar `timestamp` y `event_type` en SQL; refinar tags en Pandas; convertir timestamps con `pd.to_datetime(..., utc=True)` antes de agrupar; no cargar la tabla completa ni calcular métricas en routers. `GET /telemetry/report` resuelve una ventana de 7 días por defecto y usa caché TTL 60 s. No convertirlo en reporte de negocio ni escribir en `telemetry_events`.

Este archivo está dentro de `.agents/` y se conserva como configuración/referencia del repo; no se elimina durante la limpieza de los documentos raíz.

## 11. Diseño de reporting semanal — `SPECSPIPELINE1.md`

Diseñar antes de orquestar un pipeline Prefect desde `telemetry_events` (solo lectura) hacia `reporting.weekly_location_performance`: KPI de costo de compras, costo/ratio de merma, frecuencia de quiebre y alertas de precio. Grano `(location_id, week_start ISO)`, moneda local separada; no sumar ni convertir COP/USD. Documentar estado actual/brecha, extracción-transformación-carga, upsert idempotente, logs/run IDs, checkpoints y bloques de Prefect. Planear API `services/reporting/` para estado, ejecución manual y consulta de KPI; mantener `services/telemetry/analysis.py` y `/telemetry/report` intactos.

El diseño debe responder explícitamente estos diez casos: (1) deduplicación del origen con `eventId` y capa responsable; (2) reintento tras carga parcial sin duplicados; (3) eventos tardíos y recálculo/auditoría de ventana; (4) distinguir silencio real de captura caída mediante heartbeat; (5) trazar `eventId`/`requestId`/`run_id`; (6) distinguir crecimiento de volumen de pérdida/duplicación; (7) checkpoint al caer la base; (8) buffer offline y dedupe server-side; (9) reintento de POST con `Idempotency-Key` y respuesta a duplicado; (10) bloqueo ante cron/manual concurrentes.

## 12. Implementación resiliente del pipeline — `SPECSPIPELINE2.md`

Implementar flow Prefect en `data/pipelines/pipeline.py` con tasks explícitas ETL, retries/retry delay documentados para servicios externos, al menos una task no crítica invocada con `return_state=True`, caché de transformación con clave/TTL, carga upsert idempotente y metadata de corrida (inicio/fin/procesados/estado/error). Preservar CLI `python data/pipelines/pipeline.py`. `services/reporting/` importa el pipeline y ofrece endpoints autenticados separados para estado, disparo y consulta de KPI; el API no duplica ETL.

## 13. Subflows, tests y dashboard de reporting — `SPECSPIPELINE3.md`

Refactorizar el pipeline anterior en ≥3 `@flow` subflows coordinados: extracción, transformación y carga con entradas/salidas explícitas. Mantener CLI. `tests/pipelines/test_pipeline.py` debe probar ≥3 tasks de transformación aisladas, fixture in-memory, entrada malformada y un valor KPI calculado a mano. Construir dashboard de backoffice para Mariana/Felipe consumiendo el endpoint reporting: mostrar los cinco KPIs con nombres del contexto y período claramente etiquetado.

## 14. Forecast de ventas — `SPECSPREDICCIONVENTAS.md`

Usar el dataset real `data/raw/brasaland_sales.csv`, no simularlo. Target: revenue USD de fila consolidated; cronología mensual, split primeros 8 años/últimos 2. Tratar nulos, features causales de lag/rolling/calendario sin leakage, modelo Random Forest o XGBoost con `random_state` fijo y justificación. Reportar MSE/PSI/Gini/K2 en prueba, explicar métricas y elección, visualizar predicción con variabilidad y test de split. Contexto del CSV, patrón estacional y limitación de disponibilidad están en contexto maestro.

## 15. Evaluación temporal del forecast — `SPECSEVAL.md`

Sobre el modelo reproducible, implementar ≥5 folds temporales sin shuffle y sin leakage de features entre límites; reportar métrica como media ± desviación. Generar curva de aprendizaje en `data/eval/`; calcular MAE y RMSE train/validation; justificar métrica principal según costo de sobre/subestimar. `evaluation_report.md` clasifica explícitamente ajuste (underfit/overfit/bien ajustado) según curvas/CV y propone acción correctiva concreta. Test verifica orden temporal de folds.

## 16. Grafo de agente LangGraph — `SPECSLANGRAPH1.md`

Extender RAG existente sin reescribirlo: estado mínimo explícito, nodos separados receive/retrieve/generate, edges condicionales (entrada vacía y contexto ausente), compilar antes de ejecución, checkpointing y trace consultable por corrida. Endpoint `/agent/query` invoca el grafo y no expone stack traces. ≥3 evals en `tests/pipelines/`, contra criterios de trace/ruta y anclaje RAG, además de tests RAG existentes. Ningún nodo encapsula `query()` monolítico si eso repite retrieve.

## 17. MCP de empresa — `SPECSMCP.md`

Servidor independiente bajo `mcps/` con FastMCP/SDK, transporte HTTP para clientes remotos, OAuth/OIDC resource server con `mcpauth` (Protected Resource Metadata, JWT bearer, audiencia/scopes; no FastMCP auth integrada). Tools descubiertas documentan nombres, schemas y límites: create/get/cambiar estado de incidencias usando `/api/incidents/{id}/status`; leer inventario; denegar explícitamente toda escritura de inventario. Least privilege/scopes, errores diferenciados y log por invocación. El mismo agente consume el MCP mediante `langchain-mcp-adapters`, sin camino directo alterno. Playground público requiere OIDC real y port-forward Codespaces; registrar si sigue pendiente.

## 18. Memoria episódica — `SPECSAGENTMEMORY.md`

Extender el mismo manager-support agent con store persistente separado de `*_knowledge`; lectura/escritura explícita. Proponer solo correcciones operativas recurrentes por sede, escalaciones repetidas o preferencias estables, con respuesta y propuesta estructuradas en una llamada; mostrar la propuesta al usuario, nunca guardar automáticamente. Clasificar approve/reject/edit contra única propuesta pendiente, auditar propuesta/mensaje/actor/decisión/confianza/tiempo; silencio/ambigüedad descarta. Continuación del mensaje vuelve al flujo normal. Privacidad y elegibilidad según contexto maestro; consolidar/deduplicar, cap y expiración, probar ciclo aprobado (visible luego) y rechazado (sin cambio).

## 19. Harness y guardrails — `SPECSHITO8.md`

Asegurar el mismo manager-support agent. Dominio operativo responde con RAG/tools; small talk y trivia permitidos de forma breve con redirección; tareas personales fuera de dominio se rechazan. System prompt inmutable ante ≥3 jailbreaks y extracción gradual de receta en tres turnos. Aislar RAG/MCP/memoria como datos no confiables; validar schema y output contra prompt leaks, recetas madre, precios/contratos, payroll/performance y PII. Tests deterministas cubren input/output guards, aislamiento externo, y no dependen de LLM vivo. Loguear redirecciones/bloqueos por tipo y exponer resumen por sesión.

## Matriz de procedencia

| Área consolidada | Documentos fuente absorbidos |
| --- | --- |
| Empresa, roles y contexto base | `CONTEXT.md`, `context-company.md` |
| Incidente CSV y gestor | `CONTEXT.md`, `CONTEXTINCIDENCIAS.md`, `SPECSINCIDENCIAS.md` |
| Auth, reset y QA | `CONTEXTBULLET.md`, `CONTEXTPASSRESET.md`, `SPECSBULLET.md`, `SPECSPASSRESET.md` |
| RAG y grafo | `CONTEXTCONOCIMIENTO.md`, `SPECSCONOCIMIENTO.md`, `SPECSLANGRAPH1.md` |
| Telemetría/reporting | `CONTEXTTELEMETRY.md`, `CONTEXT-empresa.md`, `CONTEXTPIPELINE1.md`, `SPECSTELEMETRY.md`, `SPECSPIPELINE1.md`, `SPECSPIPELINE2.md`, `SPECSPIPELINE3.md` |
| Forecast/evaluación | `CONTEXTPREDDICCIONVENTAS.md`, `CONTEXTEVALUACION.md`, `SPECSPREDICCIONVENTAS.md`, `SPECSEVAL.md` |
| Agente seguro | `CONTEXTAGENTMEMORY.md`, `CONTEXTHITO8.md`, `SPECSAGENTMEMORY.md`, `SPECSHITO8.md`, `SPECSMCP.md` |
| Plataforma y rendimiento | `SPECSDOCKER.md`, `SPECSAUDITF.md`, `SPECSCACHING.md` |

Los nombres de la tabla son identificadores históricos para rastrear el origen, no rutas canónicas vigentes. Las fuentes protegidas `CONTEXT.md` y `context-company.md` permanecen sin modificar. `.agents/SPECSTELEMETRYREPORT.md` permanece separado como artefacto de configuración/agente y no se elimina con los documentos raíz.
