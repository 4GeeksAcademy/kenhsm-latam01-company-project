# Auditoría OWASP Top 10 y riesgo de IA

Fecha de evaluación: 2026-10-25  
Referencia: OWASP Top 10 2021 (edición coherente con las categorías A01/A02/A05 del briefing).  
Alcance de código: `services/brasaland-api`, `mcps/brasaland`, `uis/website` y `uis/backoffice`, incluyendo el agente, RAG, MCP, SSE y WebSocket existentes. POS, pagos y Brasa Points se evaluaron como capacidades buscadas; no se encontraron implementaciones activas en este alcance. `supply_chain` sí tiene un endpoint de orden, pero solo actualiza estado en memoria y no llama a un proveedor. La aplicación protegida `apps/talent-pipeline-tracker` no se modificó ni se incluye como producto Brasaland.

Esta evaluación estática y sus pruebas no son una certificación de producción ni una opinión legal. Separa evidencia del código de controles del host que no son accesibles desde este Codespace.

## Línea base y correcciones

Antes de los cambios de esta auditoría:

- Compose publicaba los puertos HTTP `3000`, `3001`, `8010`, `6333` y `6334` en todas las interfaces; los dos últimos exponían Qdrant.
- Las imágenes de API y UI no definían un usuario runtime, por lo que iniciaban como root.
- La clave JWT tenía un valor débil conocido por defecto.
- Cualquier usuario con JWT válido podía crear/cambiar incidentes y seleccionar tools del agente, incluidos los cambios de estado.
- La orden de compra de demostración era creada inmediatamente en memoria por cualquier usuario autenticado; no existía una fase de aprobación.

Correcciones aplicadas:

- Las imágenes ahora ejecutan como usuarios no-root; el API escribe bases, checkpoints y archivos RFP en `/var/lib/brasaland`, con volumen dedicado.
- Los puertos de UI y API publicados por Compose se ligan a `127.0.0.1`; Qdrant conserva su red interna de Compose pero ya no publica puertos al host.
- `SECRET_KEY` ahora es obligatoria y requiere al menos 32 caracteres; no se conserva una clave de respaldo.
- Las mutaciones de incidentes y las tools del agente requieren rol `manager` o `admin`.
- Las órdenes simuladas se crean como `pending_approval`; solo otra identidad `manager`/`admin` puede aprobarlas. Se aplica a todas las órdenes porque el contrato no contiene costo ni el equipo definió un umbral. La aprobación solo cambia el registro en memoria; no se comunica con proveedores.

Esto endurece el Compose de desarrollo, no crea HTTPS ni sustituye un firewall de producción.

## Servidor y red

| Control | Evidencia y estado |
| --- | --- |
| Usuario no-root | Aplicado a las imágenes API/UI y explícito en el servicio backend Compose: [services/Dockerfile](../../services/Dockerfile#L3), [uis/Dockerfile](../../uis/Dockerfile#L17), [docker-compose.yml](../../docker-compose.yml#L29). El almacenamiento persistente del API está separado del código. |
| Puertos de aplicación | Compose solo publica UI/API en loopback; Qdrant no tiene `ports`: [docker-compose.yml](../../docker-compose.yml#L9). |
| HTTPS/TLS | No hay proxy TLS ni certificado/configuración de producción en el alcance. Compose sirve HTTP local; antes de tráfico externo debe existir un reverse proxy que exponga HTTPS/WSS y no publique los puertos internos. |
| SSH/root SSH | No verificado. `id` y `ss -tulpn` se ejecutaron dentro del contenedor de desarrollo, no en el host de producción; no prueban `PermitRootLogin`, usuarios operativos ni firewall. `ss` mostró puertos del runtime Codespaces, no servicios de Brasaland. |
| Firewall/permisos del host | No verificado ni modificado: el repositorio protege `infra/` y el entorno no proporciona acceso al host. Hace falta una ejecución autorizada en el servidor para verificar firewall, SSH, propietario/permisos de código, logs y secretos. |

No afirmar que root SSH está deshabilitado o que el firewall de producción está cerrado hasta contar con evidencia del host. El Compose actual es un control local adicional, no evidencia del perímetro exterior.

## Inventario de IA y privacidad

| Componente | Estado y riesgo/controles observados | Responsable |
| --- | --- | --- |
| Agente de soporte a gerentes (`manager_support`) | Implementado. RAG de lectura; las tools quedan limitadas a `manager`/`admin`. Las acciones de inventario por escritura son rechazadas por MCP. | Nicolás Park / CTO y Squad de Backend |
| Asistente de entrenamiento RAG | Implementado sobre la base de conocimiento. El contenido recuperado se marca como dato no confiable, se aísla del rol de sistema y la salida se valida. La prueba de inyección indirecta descrita abajo pasa. | Jake Morrison / Formación y Squad de Backend |
| MCP de incidentes/inventario | Implementado con OAuth/OIDC, scope global y scopes por tool. Inventario es de solo lectura; `write_inventory` siempre deniega sin llamada a la API. Los cambios de estado de tickets usan endpoint específico y transición validada. | Nicolás Park / CTO y Squad de Backend |
| Dashboard de tickets en tiempo real | Implementado. SSE RFP usa endpoint autenticado y el chat operativo usa WebSocket autenticado. El JWT del WebSocket actualmente viaja en query string, riesgo residual de exposición en logs de URL. | Squad de Backend / Nicolás Park |
| Pipeline de pedidos a proveedor sugeridos por IA | No hay pipeline agéntico ni integración externa. El endpoint de demostración crea una orden en memoria y ahora exige aprobación humana independiente antes de marcarla aprobada. | Lucía Fernández / Compras y Proveedores |

### NIST AI RMF y marco regulatorio

Este resumen usa las funciones **Govern, Map, Measure y Manage** del NIST AI Risk Management Framework como organización de riesgos; no declara conformidad formal.

- **Govern:** se asignan responsables en el inventario; las tools sensibles requieren rol. El flujo RFP existente usa aprobación humana identificada y las órdenes de demostración requieren aprobador distinto del solicitante. Las métricas globales de guardrails aún son de proceso y necesitan almacenamiento/alertas compartidas en despliegues multi-worker.
- **Map:** hay datos y operaciones en Colombia y Florida. El sistema no debe revelar PII/Brasa Points, datos de empleados ni secretos de proveedores; el briefing confirma que Brasaland no procesa PHI.
- **Measure:** se ejecutan pruebas deterministas de jailbreak, aislamiento de RAG, autorización por rol, aprobación de órdenes y suites RFP/MCP; los escáneres de dependencias ejecutados no reportaron vulnerabilidades conocidas.
- **Manage:** se cerró la exposición directa de Qdrant en Compose, se eliminó el secreto JWT por defecto y se restringieron writes. El host, TLS, firewall, SSH y telemetría central siguen pendientes de verificación de despliegue.

Marcos explícitos para datos personales de clientes, pagos y empleados:

- **Colombia: Ley 1581 de 2012.** Requiere autorización del titular para el tratamiento y notificación a la Superintendencia de Industria y Comercio ante incidentes que comprometan datos personales, a la mayor brevedad posible.
- **Florida (EE. UU.): Florida Information Protection Act (FIPA).** La notificación a afectados y, cuando aplique, al Attorney General debe ocurrir dentro de los 30 días posteriores a detectar una brecha cubierta.
- Se deben considerar ambos regímenes simultáneamente y aplicar el control más estricto pertinente; la respuesta legal concreta depende de los datos afectados y asesoría competente.

### Inyección de prompt reproducible

La prueba `test_untrusted_rag_content_is_isolated_and_cannot_override_system` suministra un documento recuperado que intenta reemplazar instrucciones y obtener receta/costo de proveedor. Verifica que el mensaje de sistema conserva su rol, que el documento se envía como `UNTRUSTED_RAG_DATA` y que el marcador parecido a token de sistema se escapa. Resultado: neutralizado antes de que el contenido recuperado pueda actuar como instrucción.

Comando ejecutado:

```sh
SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest services/brasaland-api/tests/test_agent_guardrails.py -q
```

Resultado: 17 tests pasan. La prueba sustituye el proveedor LLM por un doble determinista; demuestra el aislamiento de prompt/canal, no una garantía general ante cualquier modelo o documento.

## Confirmación humana para acciones de alto impacto

- **Órdenes a proveedor:** el endpoint simulado crea `pending_approval`; el solicitante no puede aprobar su propia orden y otro `manager`/`admin` debe confirmar. Se aplica a todas las órdenes porque falta importe y no existe umbral de negocio definido. La confirmación no ejecuta una compra externa.
- **Campañas masivas/push, ajustes de puntos Brasa Points y cambios de estado de proveedores:** no se encontraron endpoints ni tools que realicen estas operaciones. El agente no puede activarlas; siguen siendo capacidades no implementadas y requieren un gate humano de servidor antes de añadirse.
- **RFP:** requiere decisiones humanas autenticadas para aprobar, rechazar o pedir cambios, y deriva el aprobador del perfil autenticado: [router.py](../../services/brasaland-api/src/brasaland_api/modules/rfp_intake/router.py#L302), [test_rfp_intake.py](../../services/brasaland-api/tests/test_rfp_intake.py#L78). Esa aprobación de propuesta no equivale a una orden de compra ejecutada.

Pruebas de aprobación de orden: [test_backoffice.py](../../services/brasaland-api/tests/test_backoffice.py#L59) verifica rol, estado pendiente, rechazo de autoaprobación y aprobación por otra identidad.

## Matriz OWASP Top 10

Cada fila evalúa backend, frontend y agente por separado. “Sin hallazgo observado” no equivale a garantía de ausencia.

| Categoría (2021) | Backend | Frontend | Agente / MCP |
| --- | --- | --- | --- |
| **A01 Broken Access Control** | **Corregido parcialmente:** writes de incidentes y órdenes requieren `manager`/`admin`; sigue faltando autorización por local en las lecturas de incidentes de usuarios autenticados. [deps.py](../../services/brasaland-api/src/brasaland_api/core/deps.py#L42), [incidents/router.py](../../services/brasaland-api/src/brasaland_api/modules/incidents/router.py#L17), [supply_chain/router.py](../../services/brasaland-api/src/brasaland_api/modules/supply_chain/router.py#L29) | La UI no es límite de autorización; el API decide. El token se conserva en `localStorage`, por lo que una XSS en el origen tendría impacto de sesión. [manager-chat.js](../../uis/backoffice/manager-chat.js#L57) | **Corregido:** tools del agente requieren `manager`/`admin`; MCP aplica scope por tool. Inventario tiene write-denial explícita. [agent/router.py](../../services/brasaland-api/src/brasaland_api/modules/agent/router.py#L63), [server.py](../../mcps/brasaland/src/brasaland_mcp/server.py#L184) |
| **A02 Cryptographic Failures** | **Corregido:** no hay clave JWT predeterminada; exige 32+ caracteres. Contraseñas se hashean con bcrypt y reset tiene propósito separado, un solo uso y expiración acotada. TLS de producción sigue pendiente. [config.py](../../services/brasaland-api/src/brasaland_api/core/config.py#L16), [security.py](../../services/brasaland-api/src/brasaland_api/core/security.py#L16) | **Riesgo residual:** JWT en `localStorage` y query string del WebSocket; usar HTTPS/WSS y redactar URLs en proxy/access logs, o migrar a un canal que no exponga el token en URL. [manager-chat.js](../../uis/backoffice/manager-chat.js#L89) | OAuth/OIDC verifica issuer, audience y scopes; la credencial de API del servicio MCP debe provisionarse fuera del repo y nunca registrarse. La URL/issuer por defecto es local y no sirve como configuración de producción. [server.py](../../mcps/brasaland/src/brasaland_mcp/server.py#L25) |
| **A03 Injection** | Validación de modelos HTTP y errores genéricos; no se observó query SQL construida desde texto de usuario en el alcance leído. | Incidentes escapan HTML y mensajes del chat usan `textContent`; no se observó interpolación de datos de cliente sin escapar en esos flujos. [main.js](../../uis/backoffice/main.js#L214), [manager-chat.js](../../uis/backoffice/manager-chat.js#L243) | Guardrail de entrada, aislamiento/escape de RAG y validación estructurada de salida; prueba indirecta reproducible pasa. [guardrails.py](../../services/brasaland-api/src/brasaland_api/modules/agent/guardrails.py#L126), [test_agent_guardrails.py](../../services/brasaland-api/tests/test_agent_guardrails.py#L123) |
| **A04 Insecure Design** | Orden de compra ahora requiere confirmación humana independiente; no ejecuta transacciones externas. No existen acciones de puntos, campañas o cambio de proveedor. | La UI no puede aprobar una orden sin pasar por el endpoint autenticado; la autorización no se delega al cliente. | Inventario solo lectura. Las tools disponibles crean/actualizan tickets y requieren rol; no hay tools de campañas, lealtad o ejecución de órdenes. |
| **A05 Security Misconfiguration** | **Corregido en Compose:** imágenes no-root, estado separado, API en loopback y Qdrant sin publicación. No existe proxy/TLS ni configuración de host verificada. Errores 500 son genéricos. [Dockerfile](../../services/Dockerfile#L3), [docker-compose.yml](../../docker-compose.yml#L9), [main.py](../../services/brasaland-api/src/brasaland_api/main.py#L73) | Compose liga los dev servers a loopback; el servidor estático de desarrollo no configura cabeceras de seguridad de producción. No desplegarlo directamente a Internet. | MCP exige bearer/scopes, pero no está desplegado por Compose; endpoint público, TLS, firewall y configuración real del issuer son verificaciones pendientes. [server.py](../../mcps/brasaland/src/brasaland_mcp/server.py#L235) |
| **A06 Vulnerable and Outdated Components** | `pip-audit --local` en el entorno instalado del API: sin vulnerabilidades conocidas. | `npm audit --audit-level=high` en website y backoffice: 0 vulnerabilidades reportadas en cada UI. | `pip-audit --local` en MCP: sin vulnerabilidades conocidas. Estos resultados son del 2026-10-25; deben repetirse en CI y ante cambios de lockfile. |
| **A07 Identification and Authentication Failures** | JWT bearer y usuarios activos se verifican; roles limitan writes. Recuperación no revela existencia del correo; token de reset vence y no es reutilizable. [deps.py](../../services/brasaland-api/src/brasaland_api/core/deps.py#L14), [security.py](../../services/brasaland-api/src/brasaland_api/core/security.py#L39) | El chat pide JWT y valida WebSocket antes de aceptar; el almacenamiento en navegador aumenta el impacto potencial de XSS. No hay auth local que sustituya al API. [chat.py](../../services/brasaland-api/src/brasaland_api/modules/agent/chat.py#L340) | MCP exige `mcp:access` más scope por tool; RAG de consulta sin tool puede ser anónimo, pero no obtiene memoria personal ni acciones. Tools requieren identidad autenticada y rol autorizado. |
| **A08 Software and Data Integrity Failures** | Dependencias bloqueadas y RFP limita tamaño/tipo declarado del PDF; no se observó verificación criptográfica de procedencia del documento. Mantener uploads/corpus como entrada no confiable. [router.py](../../services/brasaland-api/src/brasaland_api/modules/rfp_intake/router.py#L30) | No se observó carga de scripts remotos en la página pública examinada. La integridad de assets de producción depende del servidor/CDN aún no definido. | RAG trata los documentos recuperados como no confiables; no hay atestación de origen/firma del corpus. La prueba cubre inyección de instrucciones, no integridad del ciclo de publicación. |
| **A09 Security Logging and Monitoring Failures** | Errores se devuelven sin stack trace; el logging/telemetría no demuestra alertas centralizadas de seguridad ni respuesta global. | Las vistas muestran estado/error, pero no son auditoría de seguridad. | MCP registra tool, cliente y resultado sin token/contenido; contadores de guardrails son de proceso y requieren backend/alertas compartidas para operación multi-worker. [server.py](../../mcps/brasaland/src/brasaland_mcp/server.py#L81), [guardrails.py](../../services/brasaland-api/src/brasaland_api/modules/agent/guardrails.py) |
| **A10 Server-Side Request Forgery (SSRF)** | No se observó endpoint que acepte una URL arbitraria y la solicite; destinos de API/proveedor vienen de configuración de servidor. Confirmar de nuevo si se agregan importaciones por URL/webhooks configurables. | El browser llama al endpoint API configurado; no hay backend web que resuelva URLs suministradas por el cliente en este alcance. | MCP tools aceptan IDs/valores de dominio, no URLs arbitrarias; endpoints remotos vienen de configuración del servidor. Sin hallazgo SSRF observado en estas tools. |

## Evidencia y pendientes

Comprobaciones ejecutadas:

- `docker compose config --quiet`: configuración válida.
- `SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest services/brasaland-api/tests/test_security.py -q`: 6 tests pasan.
- `SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest services/brasaland-api/tests/test_incidents_mcp_contract.py -q`: 5 tests pasan, incluyendo denegación de writes/tools al rol `user`.
- `SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest services/brasaland-api/tests/test_agent_guardrails.py -q`: 17 tests pasan.
- `SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest services/brasaland-api/tests/test_backoffice.py -q`: 7 tests pasan, incluyendo aprobación independiente de órdenes.
- `SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest services/brasaland-api/tests/test_agent_memory.py services/brasaland-api/tests/test_agent_memory_flow.py -q`: 11 tests pasan.
- `SECRET_KEY=test-only-key-with-at-least-32-characters uv --project services/brasaland-api run pytest services/brasaland-api/tests/test_rfp_intake.py -q`: 22 tests pasan.
- `uv run --project mcps/brasaland pytest mcps/brasaland/tests/test_mcp_server.py -q`: 6 tests pasan.
- `npm --prefix uis/website audit --audit-level=high` y `npm --prefix uis/backoffice audit --audit-level=high`: 0 vulnerabilidades reportadas en cada UI.
- `uv run --project services/brasaland-api --with pip-audit pip-audit --local` y el equivalente para `mcps/brasaland`: no vulnerabilities found.

Pendientes antes de un sign-off de producción:

1. Un operador autorizado debe verificar usuario SSH no-root, `PermitRootLogin` deshabilitado, permisos de directorios y firewall en el host; este workspace no permite hacerlo ni modificar `infra/`.
2. Desplegar detrás de HTTPS/WSS, sin publicar API/Qdrant/MCP/DB/Redis directamente; añadir cabeceras de seguridad y redacción del JWT del WebSocket en logs.
3. Definir autorización por `location_id` para lecturas de incidentes antes de usar datos de varias sedes con roles manager.
4. Añadir almacenamiento/alertas de auditoría compartidos y validación de procedencia del corpus RAG.
5. Antes de conectar órdenes de compra a un proveedor, definir monto/umbral, moneda, segregación de funciones y confirmación humana en servidor; el endpoint actual solo simula el registro en memoria.
