# Prácticas seguras de IA: evaluación NIST CSF 2.0

Fecha: 2026-10-25  
Ámbito: componentes de IA y superficies conectadas construidos para Brasaland en este repositorio. Es una revisión de código y configuración local, no una certificación de despliegue ni una opinión legal. Complementa la matriz [OWASP Top 10](./owasp-top10-audit.md).

## Resultado ejecutivo

El agente aplica separación de instrucciones de sistema y datos no confiables, guardrails y validación de salida. Inventario vía MCP es de solo lectura; las tools requieren scopes. `/agent/query` limita por IP y el chat WebSocket por identidad. El endpoint interno `/knowledge/query` también exige JWT/rol manager-admin, comparte cuota y sanitiza entrada. Todos limitan entradas a 3000 caracteres y limpian controles. El agente registra decisiones estructuradas sin pregunta, respuesta ni argumentos de tools.

`.env.example` existe con valores de credenciales vacíos y `.env` está ignorado por Git. Las claves se configuran por entorno; nunca deben copiarse valores reales a la plantilla. La plantilla no enumera `RESEND_API_KEY`, `BRASALAND_API_TOKEN` ni `AGENT_QUERY_LIMIT_PER_MINUTE`; el archivo está excluido de edición por el entorno y se deja como pendiente de completar. El rate limiter y los contadores de guardrails son por proceso, no defensa distribuida. TLS, firewall, SSH de producción, políticas de retención del proveedor, alertas centralizadas y restauración de backups no se verificaron.

## Inventario y responsables

| Sistema | Propósito, entradas y riesgo | Responsable del control Brasaland | Tercero / responsabilidad compartida |
| --- | --- | --- | --- |
| Agente de soporte `manager_support` | `/agent/query` recibe preguntas y acciones solicitadas; el chat recibe mensajes e historial por WebSocket. Riesgos: prompt injection, extracción de datos, abuso de costo y uso excesivo de tools. | Nicolás Park / CTO y Squad de Backend: roles, guardrails, cuota, trazas y credenciales. | Modelo OpenAI-compatible: el CTO controla endpoint/API key, minimización de datos y contrato; el proveedor administra su infraestructura de inferencia según sus términos. Antes de producción confirmar retención, entrenamiento, región, subprocesadores y DPA. |
| Asistente de entrenamiento RAG | `POST /knowledge/query` y Qdrant sirven preguntas sobre recetas, procedimientos y estándares. El endpoint ahora exige manager/admin, sanitiza/limita entrada y aplica cuota. Riesgo residual: el source del generador legacy está excluido de lectura, así que su aislamiento frente a prompt injection indirecta no pudo verificarse con la prueba existente. | Jake Morrison / Formación para autoría/publicación del corpus; Nicolás Park / CTO para retrieval, aislamiento y configuración. | Proveedor de modelo: mismo control contractual/técnico del agente, pero confirmar proveedor exacto del pipeline legacy. Qdrant es autogestionado en Compose; el CTO administra acceso, parcheo y backups. |
| MCP de incidentes/inventario | El agente recibe resultados de tickets e inventario. Riesgo: scopes excesivos, token filtrado o write accidental. MCP usa OAuth/OIDC, scopes separados y niega escritura de inventario. | Nicolás Park / CTO y Squad de Backend: configuración de issuer/audience, scopes y token de servicio. | El proveedor OIDC no está identificado en el repo: su operador protege autenticación/JWKS; Brasaland valida issuer, audience, scopes y rotación. No asignar `inventory:write`. |
| Flujo RFP con agentes | PDF autenticado alimenta clasificación, extracción, trabajadores por área, evaluación y síntesis; salidas esperan aprobadores humanos. Riesgos: inyección en documentos, fuga contractual y decisiones erróneas. | Lucía Fernández / Compras para datos comerciales; Camila Ospina / Marketing para intake/reapertura; Nicolás Park / CTO para proveedor, claves, límites y persistencia; los aprobadores nombrados para sign-off. | El proveedor LLM de cada subgrafo RFP no se pudo verificar en el código accesible. Identificar proveedor, retención, región y DPA antes de producción; no asumir que es el mismo del agente. |
| Pronóstico de ventas | Modelo Random Forest sobre CSV mensual y evaluación temporal; no es agente ni ejecuta acciones. Riesgos: datos alterados, leakage y uso fuera de muestra. | Squad Data / Nicolás Park; Finanzas valida decisiones derivadas. | Scikit-learn es dependencia local, no proveedor remoto de inferencia. Controlar lockfile y escaneo de paquetes. |
| Dashboard SSE/WebSocket | Presenta tickets y conversación; no debe ser límite de autorización. Riesgo: JWT/origen/logs y exposición entre sedes. | Nicolás Park / CTO y Squad de Backend: autenticación, autorización, TLS, redacción de logs y broker. | Hosting/reverse proxy: TLS y acceso de red; debe redactar el token WebSocket que hoy viaja en query string. |

## Entradas no confiables que alcanzan modelos

| Punto | Datos | Controles actuales / pendiente |
| --- | --- | --- |
| `POST /agent/query` | Pregunta del usuario y solicitud de tool | 3000 caracteres, limpieza de controles, guardrail antes de retrieval/tools, rol para tools, cuota por IP y validación de salida. |
| `WS /agent/chat/{session_id}` | Mensajes, redirecciones e historial | JWT en handshake, sesión ligada a usuario/local, limpieza antes de persistir, 3000 caracteres y cuota por identidad. JWT en query string requiere WSS y redacción en proxy. |
| `POST /knowledge/query` | Pregunta a RAG de entrenamiento y corpus de proveedores/lealtad | JWT manager/admin, limpieza, 3000 caracteres y cuota. El cuerpo interno del prompt de `data/pipelines/rag.py` no pudo revisarse por exclusión del workspace; confirmar roles de sistema/usuario, aislamiento de corpus y salida antes de producción. |
| Qdrant `brasaland_knowledge` | Texto/metadatos de documentos RAG | Se serializa como `UNTRUSTED_EXTERNAL_DATA`, se escapa y no reemplaza el rol de sistema. `test_untrusted_rag_content_is_isolated_and_cannot_override_system` prueba una instrucción para revelar receta/costo. |
| Tools MCP | Resultados de tickets/inventario y errores de API | OAuth global + scope por tool, esquemas tipados y contrato de salida; resultados tratados como datos no confiables. Inventario no tiene escritura. |
| Memoria aprobada e historial | Hechos operativos consentidos y mensajes previos | Aislamiento por usuario, consentimiento, filtros de PII, retención acotada y serialización como datos no confiables. |
| Intake RFP | PDF y texto extraído para clasificación/redacción | Upload autenticado, límite de 25 MiB, evaluación y aprobaciones. Pendiente confirmar detección real de tipo, proveedor, retención y eliminación de documentos en producción. |
| Forecast | CSV estructurado de ventas | No se envía a un LLM. Evaluación temporal reduce leakage; falta certificar procedencia/versionado del dataset de despliegue. |

Los prompts mantienen los roles `system` y `user` separados. `sanitize_user_input` limpia y limita la entrada antes de guardrail/grafo; `sanitize_untrusted_text` escapa datos externos; `validate_model_output` rechaza salidas sensibles o estructuralmente inválidas antes de mostrar o persistir propuestas.

## NIST CSF 2.0: seis funciones

| Función | Estado/evidencia | Acción concreta y prioridad |
| --- | --- | --- |
| **Govern** | Responsables listados arriba; existen política de datos, scopes y aprobación. El proveedor OIDC y el modelo RFP no están fijados/documentados aquí. | **P1:** CTO mantiene registro de proveedores, modelo/versión, endpoint, ubicación, retención, DPA/subprocesadores y dueños de claves. Los dueños de negocio aprueban finalidad y datos permitidos. No liberar a producción hasta confirmar contratos. |
| **Identify** | Componentes, entradas y jurisdicciones mapeados. Los datos sensibles incluyen Brasa Points, pagos, nómina y contratos; Brasaland declara no tratar PHI. | **P1:** mantener mapa por endpoint/tool, datos, local/país, proveedor y retención; revisar ante cambios. Antes de POS/loyalty, hacer evaluación específica de datos y permisos. |
| **Protect** | Secretos por entorno; `.env` ignorado; entrada saneada/limitada; output validado en `manager_support`; scopes/roles; cuotas HTTP/WS/RAG; aprobación independiente de orden demostrativa. Inyección neutralizada en el grafo de `manager_support`, no verificada en el generador RAG legacy. | **P0 aplicado en código:** conservar barreras y cuota configurable de 20/min. **P1:** inspeccionar/retirar el generador legacy o probar su aislamiento; cuota distribuida, WSS/TLS, evitar JWT en URL, scopes por local, secret manager y CORS de despliegue. |
| **Detect** | Logs de guardrails y MCP. `agent_run_completed` registra request ID, actor seudonimizado, acción, decisión/categoría, ruta y nodos, sin contenido de usuario ni argumentos. | **P1:** centralizar logs/alertas con acceso y retención limitados; alertar por bloqueos, 429, tools anómalas y fallos de auth. Confirmar redacción del JWT en logs del proxy. |
| **Respond** | No hay playbook operativo/guardia demostrable en este checkout. | **P1:** CTO contiene el incidente (deshabilitar endpoint/tool, revocar tokens, aislar proveedor), preserva logs y determina datos/sedes/países. Coordinar a Mariana Restrepo, dueños de datos y asesoría legal. Para Colombia, notificar a la SIC a la mayor brevedad posible; para una brecha cubierta por FIPA, notificar afectados y, cuando aplique, al Attorney General dentro de 30 días desde detección. La aplicación legal concreta requiere asesoría competente. |
| **Recover** | Datos pueden residir en TinyDB/SQLite, Qdrant y Supabase. No hay evidencia de restauración operacional probada ni RTO/RPO aprobado. | **P1:** dirección y CTO fijan RTO/RPO; habilitar backups cifrados y separados para TinyDB, memoria/chat, checkpoints, Qdrant y DB; ensayar restore, rotar credenciales y reabrir en modo lectura tras validar integridad/guardrails. No declarar recuperación lista hasta superar un restore test. |

## Acciones irreversibles

- Campañas masivas/push, ajustes/anulaciones de Brasa Points y cambios de estado de proveedor no tienen tools/endpoints ejecutables en el alcance. El agente no puede activarlas; cualquier implementación futura exige aprobación humana de servidor, permisos, idempotencia y auditoría.
- La orden de compra actual es un stub en memoria: se crea como `pending_approval`; quien solicita no puede aprobar y otra identidad `manager`/`admin` debe confirmar. No se envía a proveedor y no incluye importe/umbral. Compras debe definir monto, moneda y umbral antes de integración real.
- MCP `write_inventory` falla cerrado y no llama a la API. Las transiciones de incidentes no equivalen a aprobación de compras.
- RFP requiere sign-off autenticado de los responsables; no cursa por sí mismo una orden comercial.

## Ruta priorizada

1. **P0, aplicado y probado:** secreto JWT sin fallback, contenedores no-root y puertos de Compose restringidos (ver informe OWASP), sanitización, límites HTTP/WS, mínimo privilegio, aprobación de orden demostrativa y logs de decisión sin contenido sensible.
2. **P1, antes de producción:** revisar la seguridad de `data/pipelines/rag.py` (generador no inspeccionable aquí) y demostrar aislamiento de prompt injection; completar variables que faltan en `.env.example`; secret manager; HTTPS/WSS; identificar modelo RFP y proveedor OIDC; redactar tokens; autorización por local; cuota distribuida; alertas; verificar firewall y SSH no-root en el host. Estos controles de host no se pudieron comprobar desde Codespaces.
3. **P1, resiliencia y privacidad:** probar backups/restore y fijar RTO/RPO; ensayar playbook; confirmar región, retención, borrado y subprocesadores de proveedor LLM, Supabase, Resend y OIDC.
4. **P2, nuevas capacidades:** antes de POS/loyalty, campañas o compra real, exigir threat model, segregación de funciones, umbral por moneda/local, approval API idempotente, audit trail durable y pruebas de exfiltración; hasta entonces, mantenerlas fuera de las tools.

## Evidencia reproducible

```sh
SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest \
  services/brasaland-api/tests/test_agent_guardrails.py \
  services/brasaland-api/tests/test_agent_chat.py -q
```

Las pruebas `test_agent_query_returns_429_when_client_exceeds_rate_limit`, `test_websocket_sanitizes_input_and_rate_limits_model_turns`, `test_agent_input_is_sanitized_before_guardrail_and_model`, `test_agent_run_logs_decision_without_prompt_or_response` y `test_untrusted_rag_content_is_isolated_and_cannot_override_system` comprueban cuota, sanitización, trazabilidad sin prompt y neutralización de inyección. Ejecutar solo con una clave de prueba, nunca con credenciales reales.

Limitaciones: cuota en memoria por proceso; logs en stdout sin SIEM; no se verificaron contrato/retención de proveedores, configuración de red/host ni recuperación desde backup.
