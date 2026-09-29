# Plan de telemetria Brasaland

## Objetivo y alcance

Este documento define que capturar, por que, con que contrato y con que urgencia de entrega. Es un diseño previo a la instrumentacion: no agrega captura, almacenamiento ni servicios nuevos.

El contexto de negocio define el dominio objetivo como una cadena de 14 locales en Colombia y Florida. El repositorio actual aun no implementa ese sistema de inventario de punta a punta: `services/brasaland-api` tiene login JWT, usuarios, compras y endpoints stub de inventario/operaciones en memoria; el backoffice estatico muestra operaciones y analisis de CSV. Por eso, los eventos se clasifican como **disponibles hoy** cuando el flujo existe y **futuros** cuando dependen de ordenes reales o sesiones persistentes. Ambos grupos quedan descritos con contrato instrumentable. Ningun endpoint stub debe interpretarse como fuente de cifras de produccion.

El plan cubre las seis metricas obligatorias del contexto de telemetria y oportunidades justificadas. Los eventos obligatorios conservan exactamente su `event_type`, entidades y dimensiones de negocio. Las metricas se pueden agregar por local, pais y semana; los importes permanecen en COP o USD segun el local y nunca se convierten en la capa de captura.

## Catalogo de eventos

`event-schemas.json` es la fuente normativa de tipos, campos, obligatoriedad y allowlists. En cada evento, la frase de hipotesis y decision explica el valor de negocio u operacion. **Obligatorio** significa requerido por `CONTEXTTELEMETRY.md`; **Oportunidad** es una extension propuesta.

### Inventario y compras

| Clase | `event_type` | Hipotesis: necesitamos saber... | Decision que habilita | Estado |
|---|---|---|---|---|
| Obligatorio | `inbound_order_created` | cuanto y que compra cada local y proveedor | consolidar compras y negociar mejores precios con proveedores | Futuro: falta recepcion persistente de ordenes de entrada |
| Obligatorio | `outbound_order_created` | que ingredientes se consumen y a que ritmo por local | ajustar la sugerencia de reposicion | Futuro: falta consumo persistente de inventario |
| Obligatorio | `stock_waste_registered` | cuanto se pierde, por que razon y en que local | priorizar auditorias de merma | Futuro: falta registro real de merma |
| Obligatorio | `stock_threshold_triggered` | con que frecuencia cada local cae bajo el minimo por producto | ajustar minimo o frecuencia de reabastecimiento | Futuro: falta motor de umbrales |
| Obligatorio | `direct_stock_edit_rejected` | si el personal intenta saltarse la trazabilidad | reforzar capacitacion o permisos en locales con recurrencia | Futuro: instrumentar rechazo en API; el contrato nunca permite editar stock |
| Obligatorio | `ingredient_price_variance_detected` | cuando el precio unitario supera el umbral contra el historial del producto/proveedor | alertar a Compras para renegociar o buscar alternativa | Futuro: falta historial de precios |
| Oportunidad | `inventory_order_validation_failed` | que reglas y productos generan errores al preparar una orden | corregir formularios, catalogo o capacitacion; priorizar errores repetidos | Futuro: emitir en el validador de ordenes |
| Oportunidad | `purchase_order_created` | cuantas solicitudes de compra se crean por local y proveedor | revisar carga de compras y completar trazabilidad entre solicitud y recepcion | Parcial hoy: POST `/supply-chain/purchase-orders` es un stub en memoria |
| Oportunidad | `workflow_started` | cuantos flujos comienzan, para disponer de un denominador de conversion | comparar inicio, completitud y abandono por tipo de flujo | Parcial hoy: analisis CSV; inventario sera futuro |
| Oportunidad | `workflow_completed` | que flujos concluyen y cuanto tardan | identificar pasos lentos y mejorar conversion | Parcial hoy: analisis CSV; inventario sera futuro |
| Oportunidad | `workflow_abandoned` | en que paso se abandona una operacion y cuanto tiempo llevaba | simplificar el flujo o investigar dependencias bloqueantes | Parcial hoy: medir analisis CSV; inventario sera futuro |

### Acceso y cuentas

| Clase | `event_type` | Hipotesis: necesitamos saber... | Decision que habilita | Estado |
|---|---|---|---|---|
| Oportunidad | `auth_login_succeeded` | volumen y distribucion de accesos validos por metodo | dimensionar soporte y detectar cambios anormales de uso | Disponible hoy: `/auth/login` |
| Oportunidad | `auth_login_failed` | frecuencia y causa de credenciales rechazadas, sin recolectar la credencial | detectar abuso, fallos de cuenta o problemas de acceso y ajustar protecciones | Disponible hoy: `/auth/login` |
| Oportunidad | `session_expired` | cuantas sesiones terminan por expiracion y en que flujos ocurre | ajustar duracion del token o mejorar el reingreso | Futuro: JWT actual es stateless y no emite evento de expiracion; instrumentar validacion 401/exp |
| Oportunidad | `access_denied` | que acciones protegidas se rechazan y por que rol/regla | corregir permisos mal configurados o revisar actividad sospechosa | Disponible hoy: dependencias autenticadas y respuestas 403 |
| Oportunidad | `user_account_created` | volumen de altas y roles asignados | planificar onboarding y auditar asignacion de roles | Disponible hoy: POST `/users` |
| Oportunidad | `user_account_updated` | frecuencia y tipo de cambios de cuenta/rol | revisar gobierno de acceso y errores de administracion | Disponible hoy: PUT `/users/{user_id}` |
| Oportunidad | `user_account_deleted` | volumen de bajas y si la limpieza de acceso acompana la salida | comprobar baja oportuna de cuentas | Disponible hoy: DELETE `/users/{user_id}` |

### Uso, rendimiento y confiabilidad

| Clase | `event_type` | Hipotesis: necesitamos saber... | Decision que habilita | Estado |
|---|---|---|---|---|
| Oportunidad | `section_viewed` | que secciones usa el personal y con que frecuencia | priorizar mejoras y formacion por seccion | Disponible hoy: navegacion del backoffice; ampliar cuando haya rutas reales |
| Oportunidad | `api_latency_recorded` | cuanto tarda cada ruta/API y como cambia por ruta y estado | priorizar optimizacion y capacidad con percentiles | Disponible hoy: middleware futuro en API |
| Oportunidad | `api_request_failed` | que rutas fallan, con que status y codigo estable | priorizar correcciones y detectar regresiones | Disponible hoy: middleware/handlers de API |
| Oportunidad | `frontend_error_captured` | frecuencia y area de errores no capturados del cliente | priorizar correcciones que bloquean el trabajo | Disponible hoy: captura global de errores pendiente |
| Oportunidad | `background_job_failed` | que ejecuciones internas fallan y si se recuperan | reintentar, pausar o alertar al responsable operativo | Futuro: cuando existan jobs/pipelines |
| Oportunidad | `incident_analysis_completed` | volumen y duracion de analisis CSV y calidad resumida sin conservar el archivo | dimensionar el flujo y priorizar problemas de calidad de datos | Disponible hoy: endpoint de analisis |
| Oportunidad | `incident_analysis_failed` | en que etapa falla el analisis y con que codigo | corregir validacion, limites o disponibilidad del servicio | Disponible hoy: endpoint de analisis |

## Flujo objetivo de inventario

El camino normal preserva la regla de negocio: **no se modifica stock directamente; cada variacion procede de una orden trazable**. Cada alta de inventario representa recepcion (`InboundOrder`); cada baja representa consumo (`OutboundOrder`) o merma (`stock_waste_registered`).

1. El operador obtiene una sesion autenticada: `auth_login_succeeded`; si la autenticacion falla, `auth_login_failed`. La sesion es contexto de acceso, no una orden de inventario.
2. Abre Operaciones/Inventario: `section_viewed`. Al comenzar una orden, el cliente emite `workflow_started` con un `workflow_instance_id` UUID aleatorio; al guardar correctamente emite `workflow_completed` con el mismo ID. Si queda inactivo, `workflow_abandoned` usa ese ID y el ultimo paso, sin guardar texto ingresado.
3. La API valida producto, local, unidad, cantidad y permisos. Si la orden no pasa reglas, emite `inventory_order_validation_failed` con codigos de reglas e IDs estables de los productos afectados (cuando la falla es por linea), nunca body libre ni credenciales.
4. Al confirmar recepcion, se persiste la orden y se emite una sola vez `inbound_order_created`. Se incluye `supplier_id`; si el costo unitario cruza el umbral configurado contra el historico del mismo producto y proveedor, se emite `ingredient_price_variance_detected`.
5. Al registrar consumo de preparacion, se persiste una orden de salida y se emite `outbound_order_created`. La merma es una accion diferenciada que emite `stock_waste_registered` y una de las razones permitidas.
6. Despues del cambio confirmado, el calculo de stock compara el nuevo saldo con el minimo local. Solo al cruzar de arriba a abajo emite `stock_threshold_triggered`; no se emite en cada lectura bajo minimo.
7. Cualquier ruta/intentona de mutacion directa rechazada emite `direct_stock_edit_rejected` desde el servidor, con motivo estable y actor seudonimizado si esta autenticado.

`purchase_order_created` no equivale a `inbound_order_created`: una es una solicitud de compra al proveedor; la otra es recepcion fisica que altera stock. La API actual solo tiene la primera en memoria; las demas transiciones son objetivo futuro y requieren persistencia/idempotencia antes de considerarse fuente de negocio.

## Event Envelope y contrato de privacidad

Todos los mensajes comparten estos campos de raiz, obligatorios incluso cuando su valor sea `null`:

| Campo | Tipo/semantica |
|---|---|
| `eventId` | UUID unico por evento. Reintentos conservan el mismo ID. |
| `timestamp` | Fecha ISO 8601 UTC, por ejemplo `2026-09-27T14:05:00Z`; tiempo de ocurrencia en el origen. |
| `sessionId` | ID aleatorio de sesion, nunca JWT ni cookie. `null` para jobs sin sesion. |
| `userId` | ID interno seudonimizado estable para analitica. `null` antes de autenticar o para actor de sistema; nunca email, nombre ni telefono. |
| `event_type` | Nombre exacto `entidad_acción` en snake_case y presente en el registro JSON. |
| `schemaVersion` | Version semantica del contrato, actualmente `1.0.0`. |
| `requestId` | Correlacion entre cliente, API y logs. UUID de request; para eventos cliente sin request, UUID generado en cliente. |
| `properties` | Objeto especifico del evento, limitado estrictamente a sus claves allowlisted. |

En eventos preautenticacion (`auth_login_failed`), `userId` y `sessionId` son `null` si no existe sesion. El envelope nunca contiene email/username, password, JWT, IP completa, nombre de empleado o cliente. El ID seudonimizado se calcula fuera del almacén analitico mediante HMAC con clave protegida; la tabla de correspondencia queda separada y con acceso restringido. Si una clave de operador del sistema se representa, se usa un identificador de servicio no personal.

Todos los objetos `properties` tienen `additionalProperties: false`. La lista de claves de `properties` en cada definicion del JSON es su allowlist. Propiedades omitidas no se inventan como `null`; campos requeridos siempre deben estar disponibles o el evento se rechaza en validacion y se registra el fallo de instrumentacion sin copiar el payload original.

Para los seis eventos de inventario obligatorios se mantienen en `properties` los campos minimos del contexto: `location_id`, `country` (`CO`/`US`), `product_id`, `product_category`, `quantity`, `unit` y `currency` (`COP`/`USD`). `outbound_order_created` incluye `reason: preparation`; `stock_waste_registered` incluye `reason` con `expired`, `kitchen_error` o `theft_suspected`. Asi `reason` expresa la causa del evento; los valores de merma quedan limitados a los tres valores exactos del contexto. Los IDs son identificadores de entidad, no nombres de personas. En `stock_threshold_triggered`, `quantity` es el saldo despues del movimiento; en `direct_stock_edit_rejected`, es la cantidad intentada; en los otros eventos de orden, es la cantidad de la linea reportada. `currency` es la moneda del local y no implica que `quantity` sea un importe.

Una recepcion, salida o merma con varios productos emite un evento por linea de producto, todos con el mismo ID de orden y distinto `product_id`; esto permite agregar consumo/costo por ingrediente sin arrays opacos. `ingredient_price_variance_detected` tambien es por linea recibida. `stock_threshold_triggered` es por producto y cruce de umbral, no por consulta de stock. `purchase_order_created` resume una solicitud con `line_count` y no representa recepcion ni mutacion de stock.

## Entrega: stream o batch

Stream significa disponible en segundos para reaccionar; batch significa agregado/procesado periodicamente, no retraso en la confirmacion transaccional de la operacion. Cada evento se persiste junto al cambio de negocio mediante outbox o equivalente y se publica despues del commit; la telemetria no puede hacer fallar una orden confirmada.

| `event_type` | Entrega | Justificacion por urgencia |
|---|---|---|
| `inbound_order_created` | Batch (cada 15 min; agregado diario) | Compras consolida por local/proveedor; no requiere actuar dentro de segundos. La orden queda persistida sincronicamente. |
| `outbound_order_created` | Batch (cada 15 min; agregado diario) | El ritmo de consumo sirve para reposicion y tendencias; el ledger de stock es inmediato, el analisis no. |
| `stock_waste_registered` | Batch (cada 15 min; agregado semanal) | La auditoria compara mermas por causa/local; una demora corta no altera la respuesta operativa al registro. |
| `stock_threshold_triggered` | Stream (< 10 s) | El local necesita reponer un ingrediente antes de interrumpir servicio. |
| `direct_stock_edit_rejected` | Stream (< 10 s) | Operaciones/seguridad puede investigar intentos repetidos o ajustar permisos pronto. |
| `ingredient_price_variance_detected` | Stream (< 1 min) | Compras debe revisar un precio anomalo al recibir la mercancia, antes de acumular compras. |
| `inventory_order_validation_failed` | Batch (cada 15 min) | Sirve para identificar friccion y errores repetidos; no requiere alerta por fallo individual. |
| `purchase_order_created` | Batch (cada 15 min; agregado diario) | La negociacion y carga por proveedor se decide por volumen, no por segundos. |
| `workflow_started` | Batch (cada hora) | Es el denominador del embudo de uso y no necesita reaccion en segundos. |
| `workflow_completed` | Batch (cada hora) | Conversion y duracion son metricas de mejora de flujo, no alertas operativas individuales. |
| `workflow_abandoned` | Batch (cada hora) | Es una metrica de usabilidad agregada; una alerta individual no es accionable. |
| `auth_login_succeeded` | Batch (cada 15 min) | El volumen de acceso es analitico; la autorizacion sucede sincronicamente. |
| `auth_login_failed` | Stream (< 10 s) | Picos de rechazo pueden indicar abuso o impedir operar en un local. No incluye identificadores de credencial. |
| `session_expired` | Batch (cada 15 min) | Se usa para diagnosticar friccion de acceso; la expiracion/401 se aplica inmediatamente en el cliente. |
| `access_denied` | Stream (< 10 s) | Un patron de acceso denegado puede requerir revision inmediata de seguridad/permisos. |
| `user_account_created` | Batch (cada hora) | Altas y onboarding se revisan como volumen; el alta no depende de telemetria. |
| `user_account_updated` | Batch (cada hora) | Cambios se auditan y agregan; la autorizacion aplica al guardar, sin esperar pipeline. |
| `user_account_deleted` | Stream (< 1 min) | Una baja debe reflejarse pronto en los controles de acceso y la auditoria central. |
| `section_viewed` | Batch (cada hora) | Popularidad de secciones se decide por tendencia; no hay reaccion por visita individual. |
| `api_latency_recorded` | Batch (cada 5 min) | Percentiles por ruta requieren ventana agregada y permiten priorizar degradaciones sin alertar cada request. |
| `api_request_failed` | Stream (< 10 s para 5xx; batch de conteos para 4xx esperados) | Un pico de fallos de servidor interrumpe operaciones; validaciones esperadas se analizan en lote. |
| `frontend_error_captured` | Stream (< 30 s) | Errores que bloquean la interfaz necesitan triage rapido; el evento es acotado/sin stack bruto. |
| `incident_analysis_completed` | Batch (cada hora) | Volumen y calidad de CSV se analizan por periodos; la respuesta al usuario no espera telemetria. |
| `incident_analysis_failed` | Stream (< 30 s para fallo interno; validacion de fichero en batch) | Un fallo de servicio puede bloquear operaciones; errores previsibles de formato se agregan. |
| `background_job_failed` | Stream (< 30 s) | La operacion requiere reintentar o alertar antes de que jobs dependientes queden obsoletos. |

La publicacion stream no es una promesa de ejecucion exactamente una vez: consumidores deduplican por `eventId`. Alertas se generan por umbral/ventana, no por cada evento aislado salvo cruce de minimo o error critico.

## Throttle, debounce e idempotencia

- **Visitas:** emitir `section_viewed` una vez al completar una navegacion/cambio de seccion; ignorar repeticiones de la misma seccion durante 30 segundos. No emitir por cada render. Si la app pasa a rutas, usar ruta normalizada, nunca URL con query ni texto libre.
- **Flujos:** `workflow_started` una vez por inicio confirmado, `workflow_completed` una vez despues de la confirmacion final; ambos comparten el UUID aleatorio `workflow_instance_id`. Emitir `workflow_abandoned` una sola vez tras 30 minutos de inactividad o al salir de ruta sin completar; debounce de 2 segundos para cambios de paso. No emitir abandono si el guardado final fue confirmado; deduplicar por `workflow_instance_id`.
- **Latencia:** un evento por request de API con duracion monotonicamente medida; conservar 100% de errores y una muestra aleatoria del 10% de respuestas 2xx, estratificada por ruta/status. Agregar conteos, p50/p95/p99 cada 5 minutos. No combinar requests diferentes en el cliente.
- **Errores:** agrupar errores frontend por `error_fingerprint` + `release` y emitir como maximo uno por fingerprint/cliente cada 60 segundos; adjuntar `occurrence_count` en rango (1, 2-5, 6-20, 21+), no texto/stack libre. No muestrear errores API 5xx; agrupar alertas por ventana de 1 minuto.
- **Umbrales de stock:** emitir solo la transicion de saldo `>= minimum` a `< minimum`; rearmar al volver a `>= minimum`. Una clave idempotente incluye `location_id`, `product_id`, `threshold_version` y la transicion de stock.
- **Precios:** un evento por linea recibida que exceda la regla configurada y versionada. Suprimir duplicados de reintento por `eventId`; no ocultar una nueva recepcion real.
- **Ordenes/mermas/cuentas:** generar `eventId` al guardar y outbox transaccional; reintentos reutilizan el ID. No debounce de cambios confirmados ni descartar eventos de dominio.
- **Intentos fallidos de login:** conservar eventos, pero alertar solo por umbral agregado (p. ej. 10 fallos por clave HMAC de cuenta o 30 por clave HMAC de IP por ventana). Las claves HMAC se usan solo en un contador efimero de seguridad, se destruyen al cerrar la ventana y nunca se escriben en el evento ni en el almacen analitico.

## Riesgos, exclusiones y controles

1. **No duplicar la fuente de verdad:** el ledger/orden persistida manda. Eventos de dominio salen despues del commit y con outbox; no recalcular stock desde mensajes de telemetria.
2. **Falsos abandonos:** cierre de pestaña, red o token expirado puede parecer abandono. Marcar `completion_state` y `last_completed_step`; interpretar solo agregados, no evaluar empleados individualmente.
3. **PII en entradas libres:** excluir email/username, contrasenas, telefono, direccion, nombre, descripciones de incidencia, contenido de CSV, query strings, body HTTP, stack trace bruto, IP completa y tokens. Los codigos de error son enums/plantillas controladas; sanitizar antes de construir el evento.
4. **Datos de empleados/clientes:** no emitir nombres, IDs de clientes ni detalles personales en propiedades. `userId` del envelope es seudonimo tecnico, necesario para correlacion limitada; no es un nombre ni debe exponerse a dashboards generales.
5. **Datos financieros:** no convertir monedas ni derivar USD/COP durante captura. Las ordenes conservan moneda del local; solo agregar importes dentro de moneda homogenea. El contrato no requiere montos de venta ni cliente.
6. **Costo/volumen:** latencia exitosa muestreada y visitas agrupadas reducen volumen. Conservar eventos crudos recomendados por 90 dias y agregados sin identificadores por 13 meses; validar estos plazos con Legal/Seguridad antes de produccion.
7. **Eventos descartados:** se descarta cada tecla, clic, movimiento del raton y scroll porque genera volumen sin decision operativa concreta. No capturar grabaciones de pantalla ni contenido de formularios por privacidad. No capturar IP, user-agent completo o geolocalizacion precisa; pais/local ya son dimensiones suficientes. No inferir rendimiento individual ni ranking de empleados: el objetivo es mejorar procesos y permisos, no vigilancia.
8. **Eventos no implementados aun:** recepcion/consumo/merma, umbrales, variacion historica y abandono de orden dependen de persistencia de inventario. No fabricar datos desde los arrays stub, ni tratar una solicitud de compra como recepcion.
9. **Calidad y seguridad del pipeline:** validar schema/version, `eventId` unico, UTC, enums, moneda consistente con pais y allowlist en origen y consumidor; aislar eventos rechazados en DLQ sin payload sensible. Restringir acceso por rol, cifrar transporte/almacenamiento y auditar consultas al identificador seudonimizado.

## Secuencia recomendada de implementacion

1. Implementar envelope, generacion de `requestId`, seudonimizacion y validacion de allowlist; propagar correlacion desde cliente a API.
2. Agregar instrumentacion API de auth, autorizacion, errores y latencia, y eventos de analisis de incidencias; validar contra el JSON Schema.
3. Introducir outbox para cambios persistidos y emitir eventos de cuenta/compra; instrumentar interfaz para navegacion y abandono.
4. Solo con modelo persistente de inventario, emitir los seis eventos obligatorios en el punto transaccional definido, junto con idempotencia y reglas de umbral/precio versionadas.
5. Configurar consumidores batch/stream, alertas, retencion, controles de acceso y reconciliacion entre eventos y fuente de verdad antes de publicar dashboards.

## Criterios de aceptacion

- Los seis `event_type` obligatorios y sus dimensiones minimas coinciden con `CONTEXTTELEMETRY.md`.
- Cada registro en `event-schemas.json` tiene hipotesis, decision, entrega, sensibilidad, campos tipados y allowlist cerrada.
- El esquema valida con JSON Schema draft-07; cada evento contiene todos los campos de envelope requeridos.
- Ningun evento agrega credenciales, nombres, datos de clientes, payload libre o conversion de moneda.
- Cada decision stream/batch responde a urgencia de una accion definida y no a preferencia de implementacion.