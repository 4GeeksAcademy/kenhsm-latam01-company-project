# Contexto Maestro de Brasaland

**Fuente canónica de contexto del proyecto.** Los agentes y desarrolladores deben empezar aquí para conocer la empresa, los dominios, los contratos de datos y las restricciones compartidas. La especificación maestra correspondiente es [especificaciones-maestro.md](./especificaciones-maestro.md).

Este documento consolida los contextos de empresa y de hitos que vivían en varios `CONTEXT*.md`. Los contratos detallados se organizan por dominio, no por nombre histórico de archivo. Las referencias protegidas `CONTEXT.md` y `context-company.md` se mantienen intactas por regla del repositorio; no se usan como fuentes canónicas nuevas. Los otros contextos duplicados de la raíz ya se retiraron después de consolidar sus contratos.

## Empresa

Brasaland es una cadena de restaurantes de cocina a la brasa fundada en Medellín en 2008. Opera 14 locales en Colombia y Florida (EE. UU.), emplea aproximadamente a 115 personas y factura alrededor de USD 6 millones anuales. Su sede principal está en Medellín y tiene oficina comercial/operativa en Miami. Sus compromisos son consistencia de comida, servicio cálido y operación rápida.

Liderazgo y responsabilidades relevantes:

| Persona | Rol | Dominio |
| --- | --- | --- |
| Mariana Restrepo | CEO | Dirección ejecutiva y decisiones de cadena |
| Felipe Guerrero | Director de Operaciones | Operación de locales, turnos e incidencias |
| Lucía Fernández | Compras y proveedores | Proveedores, compras y condiciones comerciales |
| Camila Ospina | Marketing y experiencia digital | Web, fidelización y CRM |
| Ashley Turner | Personas y Cultura | RR. HH. y operación en Florida |
| Jake Morrison | Formación y estándares | Recetas, preparación y calidad operativa |
| Nicolás Park | CTO | Plataforma y tecnología |

La empresa trabaja en dos mercados y monedas: COP para Colombia y USD para Florida. Las fechas y zonas horarias deben tratarse explícitamente. La UI y el agente pueden operar en español e inglés; el idioma no determina el país del local.

## Locales

Códigos de telemetría y asignación para el gestor de incidencias:

| location_id | country | branch |
| --- | --- | --- |
| COL-01 | CO | medellin_centro |
| COL-02 | CO | medellin_laureles |
| COL-03 | CO | medellin_envigado |
| COL-04 | CO | medellin_bello |
| COL-05 | CO | medellin_itagui |
| COL-06 | CO | bogota_chapinero |
| COL-07 | CO | bogota_usaquen |
| COL-08 | CO | cali_granada |
| COL-09 | CO | barranquilla_norte |
| COL-10 | CO | central |
| FLA-01 | US | miami_doral |
| FLA-02 | US | miami_hialeah |
| FLA-03 | US | miami_kendall |
| FLA-04 | US | orlando_international |

El modelo de incidencias admite además `fort_lauderdale` y `central`; usa `central` si una incidencia de origen `internal` o `customer` no corresponde a una sede concreta. No inventes IDs de locales: la lista de arriba es el mapa conocido del proyecto.

## Incidentes

### CSV de análisis

El procesador de incidentes recibe CSV UTF-8 separado por comas con encabezado y estos campos:

- Requeridos: `incident_id` (`BRS-XXXXXX`), `date` (`YYYY-MM-DD`), `location_id`, `category`, `description` (mínimo 5 caracteres), `status`, `reporter_id` (`MGR-XX`).
- Opcionales: `customer_id` (`CLI-XXXXXX`) y `satisfaction_score` entero 1–5; el score es obligatorio si `status=CLOSED`.
- Categorías: `CUSTOMER_COMPLAINT`, `EQUIPMENT`, `SUPPLY`, `FOOD_QUALITY`, `STAFF`.
- Estados: `OPEN`, `CLOSED`, `DISCARDED`.
- Locales válidos: `COL-01`…`COL-10`, `FLA-01`…`FLA-04`.

Registros inválidos: location ausente/inválido, categoría ausente/inválida, descripción vacía/corta, reporter ausente, `CLOSED` sin score o score fuera de rango. El fixture Brasaland esperado tiene 100 filas, 96 válidas, 4 inválidas; categorías válidas: 29 quejas, 17 equipamiento, 22 abastecimiento, 19 calidad de alimentos, 9 personal; estados válidos: 32 abiertas, 50 cerradas y 14 descartadas. Para los 50 cierres con score, la distribución 1–5 es 4, 6, 12, 19, 9 y promedio 3.46.

### Gestor centralizado

El registro de incidencia del API usa `id`, `title`, `description`, `category`, `status`, `origin`, `branch`, `created_at`, `updated_at`. Categorías válidas: `equipment_failure`, `supply_issue`, `customer_complaint`, `staff_issue`, `facility_issue`, `pos_system`, `delivery_issue`, `other`. Orígenes: `customer`, `branch`, `internal`. Estados y transiciones:

- `open` → `in_progress` o `discarded`
- `in_progress` → `resolved` o `discarded`
- `resolved` y `discarded` son finales.

La carga histórica es idempotente por `incident_id`; transforma `description` a título (máximo 120 caracteres), fecha a medianoche UTC, fija `origin=customer`, convierte status/categoría y mapea `location_id` a `branch`. Totales post-transformación de 96 filas válidas: status `open=32`, `resolved=50`, `discarded=14`; categoría `customer_complaint=48`, `equipment_failure=17`, `supply_issue=22`, `staff_issue=9`.

## Autenticación

El backend usa JWT bearer y TinyDB para usuarios/perfiles. Roles: `admin`, `manager`, `user`. Endpoints de auth del producto: registro (`POST /users`), login (`POST /auth/login`), sesión actual (`GET /auth/me`), recuperación (`POST /auth/forgot-password`), reset (`POST /auth/reset-password`) y cambio autenticado (`POST /auth/change-password`). El endpoint de forgot-password no revela si existe el correo. Los tokens de reset tienen propósito separado, son de un solo uso y expiran entre 15 y 60 minutos (30 min por defecto). Las claves externas permanecen en variables de entorno; jamás se guardan aquí.

## Telemetría

### Envelope

Cada evento estándar contiene `eventId`, `timestamp` ISO 8601 UTC, `sessionId`, `userId` pseudonimizado cuando corresponda, `event_type` con taxonomía `entidad_acción`, `schemaVersion`, `requestId` de correlación y `properties` sujeto a allowlist.

### Métricas obligatorias de inventario

| event_type | Uso |
| --- | --- |
| `inbound_order_created` | Entradas de proveedor y costo de compra |
| `outbound_order_created` | Consumo de ingredientes |
| `stock_waste_registered` | Merma y sus causas |
| `stock_threshold_triggered` | Stock bajo mínimo |
| `direct_stock_edit_rejected` | Intentos rechazados de alterar stock fuera de órdenes |
| `ingredient_price_variance_detected` | Variaciones anómalas de precio |

Propiedades mínimas: `location_id`, `country` (`CO`/`US`), `product_id`, `product_category`, `quantity`, `unit`, `currency` (`COP`/`USD`); los eventos de salida/merma pueden llevar `reason`, y los tres valores de merma definidos son `expired`, `kitchen_error`, `theft_suspected`. No ampliar esos valores ni inventar taxonomías adicionales sin actualizar el contrato. No incluir nombres de empleados ni PII de clientes. La telemetría técnica (`telemetry_events`, `GET /telemetry/report`) es distinta del reporting de negocio.

## Reporting semanal de negocio

El entregable es el **Reporte Semanal de Costo y Merma por Local**, para Mariana y Felipe, fresco cada lunes. Grano: una fila por `location_id` y semana ISO, con lunes UTC como `week_start`; dimensiones `country=CO|US` y moneda local. No sumar COP y USD ni convertir moneda en v1.

KPIs exactos:

1. `total_purchase_cost`: costo de compras por local, de `inbound_order_created`.
2. `total_waste_cost`: costo de merma, de `stock_waste_registered`.
3. `waste_ratio`: `total_waste_cost / total_purchase_cost`, cero si no hay compras.
4. `stockout_events_count`: conteo de `stock_threshold_triggered`.
5. `price_alert_events_count`: conteo de `ingredient_price_variance_detected`.

La tabla destino es `reporting.weekly_location_performance`; unique key `(location_id, week_start)`. La telemetría es fuente de solo lectura; nunca escribir resultados de negocio en `telemetry_events`. La API de negocio vive en `services/reporting/`, separada de `services/telemetry/`.

Campos de destino del contrato: `id uuid`, `location_id text`, `country text`, `week_start date`, `total_purchase_cost numeric`, `total_waste_cost numeric`, `waste_ratio numeric`, `stockout_events_count integer`, `price_alert_events_count integer`, `currency text`, `computed_at timestamptz`. Los importes usan la moneda local y los agregados se vuelven a calcular/upsert por local y semana.

## Pronóstico de ventas

Dataset esperado: `data/raw/brasaland_sales.csv`, columnas `month`, `revenue_usd`, `covers_served`, `avg_ticket_usd`, `market`; target de la fila `market=consolidated`, frecuencia mensual desde 2016-01 a 2025-12. El contexto describe 120 meses, valores positivos y ningún hueco. Crecimiento anual alterna entre 3% y 7%; enero baja 12–18% frente al promedio del año previo; diciembre sube 20–30%; resto fluctúa aproximadamente ±5%. Florida representa cerca de 25% del total, no asumir mercados del mismo tamaño.

El modelo debe respetar el tiempo: primeros 8 años train, últimos 2 test; features causales de lag, rolling y calendario sin leakage. Las métricas del proyecto son MSE, PSI, Gini y K2 Score, con justificación legible para Finanzas; la evaluación añade CV temporal de al menos 5 folds, MAE/RMSE, curva de aprendizaje y diagnóstico explícito de ajuste. No simular ni sustituir el CSV si falta.

## Conocimiento RAG y agente

Corpus esperado de `docs/company-knowledge-base/`: `brasaland-loyalty-program.es.md`, `brasaland-waste-protocol.es.md`, `brasaland-menu-allergens.es.md`, `brasaland-supplier-ordering.es.md`. Colección Qdrant: `brasaland_knowledge`; payload mínimo: `company`, `source_document`, `section`, `language`, `chunk_index`, `text`. `retrieve()` filtra por score mínimo y `generate_answer(question, context)` genera solo a partir de datos recuperados; ante contexto vacío, admitirlo. Recall@3 exigido: al menos 80% en queries de evaluación; fidelidad: no introducir cifras ausentes en chunks. Alérgenos deben seguir su fuente literalmente; no afirmar “sin riesgo”. Montos se dejan en moneda de origen.

El agente persistente es `manager_support`, para managers de los 14 locales; RAG es una herramienta de lectura y MCP provee tools, no reemplazan la identidad. Dominio autorizado: estado de tickets/incidentes, inventario, procedimientos y turnos, playbooks de managers, calidad operativa. Small talk y trivia segura son breves y redirigen al trabajo de Brasaland; se rechazan ensayos, tareas escolares, código ajeno, terapia y uso personal.

No revelar: fórmulas completas/recetas madre ni proporciones exactas, términos/precios negociados con proveedores, nómina o evaluación de desempeño ajena, PII de clientes/Brasa Points fuera de una necesidad autorizada de incidente.

Memoria personal: SQLite separado de Qdrant y aislado por manager autenticado. Puede proponer correcciones operativas recurrentes por local, contexto de escalaciones repetidas y preferencias estables de comunicación. Nunca guardar PII de cliente, Brasa Points, nómina/compensación ni datos puntuales sin patrón. Propuesta → confirmación explícita/edición/rechazo; ambigüedad se descarta. Una pendiente por usuario; deduplicar por categoría/local, cap 50 hechos, leer máximo 8, propuesta expira 7 días, hechos 180 días, auditoría 730 días. Las notas son hints no verificados, inferiores a RAG/política.

Ejemplos memorables: corrección repetida del día de entrega de un proveedor por local; horario de cierre de fin de semana que cambió de forma estable; apagón recurrente que explica alertas de ventas en cero. No memorizar una pregunta puntual por el ticket promedio de ayer, un “gracias” de cierre ni una traducción de una sola vez para un reporte.

## Sistemas y diseño

- Frontend público en `uis/website`; herramientas internas en `uis/backoffice`; backend en `services/`; pipelines en `data/pipelines/`; transformación reutilizable en `data/process/`.
- Servicios Docker se llaman por nombre de servicio, no por `localhost`, cuando están dentro de Compose. Secretos por variables de entorno; no commitear `.env` ni credenciales.
- Cachear solo lecturas repetidas con TTL justificado e invalidación; no cache compartida de datos sensibles sin scope de usuario.
- Para cargas de reporting, Prefect separa extracción, transformación y carga; ETL idempotente, logs de corrida y reintentos en operaciones externas.

## Procedencia y convivencia

Este maestro consolida los contextos de hitos RAG, incidencias/CSV, auth, telemetría, reporting, ventas, evaluación, memoria y guardrails, además del perfil de empresa duplicado. `CONTEXT.md` y `context-company.md` se conservan sin cambios porque son rutas protegidas del repositorio. Los nombres de las fuentes retiradas se mantienen en la matriz histórica de especificaciones para trazabilidad. Si aparece un conflicto futuro, prima la regla más específica del dominio de esta página; se debe documentar cualquier cambio de negocio antes de implementarlo.
