# Informe de caching y carga diferida

Fecha: 2026-09-27
Alcance: `apps/talent-pipeline-tracker` y `services/brasaland-api`.

## Línea base

### Frontend

Antes de editar:

- `npm run lint`: 0 errores; 1 warning preexistente en `coverage/lcov-report/block-navigation.js` por una directiva ESLint sin uso.
- `npm run build`: correcto con Next.js 16.2.7 y Turbopack; rutas generadas: `/`, `/account/profile`, `/candidates/[id]`, `/login` y `/register`.

El proyecto no tenía un bundle analyzer ni una sesión reproducible de React Profiler en este entorno. Por eso el impacto de lazy loading se reporta como estimación basada en los límites de chunk de `next/dynamic`, no como una reducción numérica inventada.

### Backend

Se midieron cinco peticiones repetidas antes de aplicar caché, con un usuario autenticado y el servidor local en `127.0.0.1:8011`:

| Endpoint | Tiempos observados |
| --- | --- |
| `GET /operations/sales` | 4.7, 2.5, 4.1, 7.8, 11.3 ms |
| `GET /hr/employees` | 5.1, 7.1, 2.8, 2.3, 1.8 ms |

El dataset de los stubs es pequeño, por lo que las latencias no son altas todavía. La señal relevante es que ambas lecturas son repetibles, protegidas y estables; el coste evitado crecerá cuando los stubs pasen a consultas reales con más filas.

El middleware de timing quedó instalado en `main.py` y produce líneas como:

```text
GET /health -> 200 | 1.8ms
```

## Decisiones frontend

### Lazy loading

1. `CreateCandidateForm` en `app/page.tsx`: el formulario interactivo tiene estado, validación y varios campos, pero no es necesario para pintar el encabezado inicial. `next/dynamic` lo separa del chunk inicial y muestra un estado de carga corto.
2. `CandidatesTable` en `app/page.tsx`: carga todas las candidaturas, calcula filtros y renderiza una tabla potencialmente grande. Se difiere su chunk y su trabajo de cliente para que el shell inicial pueda aparecer antes.
3. `CandidateEditForm`, `CandidateUpdateControls` y `CandidateNotesSection` en `app/candidates/[id]/page.tsx`: son tres módulos interactivos que solo se usan en la ruta de detalle. Se cargan de forma diferida y cada uno tiene un placeholder independiente.

El build posterior siguió compilando correctamente, así que estos límites de carga no alteran el contrato de las rutas ni el render del servidor. El beneficio esperado es menor JavaScript inicial en las rutas que no necesitan esos módulos y menor trabajo de hidratación hasta que el componente sea requerido.

### useMemo

Se conserva y documenta la memoización ya existente en `CandidatesTable`: `filteredCandidates` recorre la colección completa, normaliza la búsqueda y aplica estado, etapa y texto. Sus dependencias son `[candidates, selectedStatus, selectedStage, searchQuery]`, por lo que evita repetir un filtrado no trivial en renders causados por cambios ajenos. `statuses` y `stages` también se derivan con `useMemo` a partir de `candidates`. No se añadieron memoizaciones a cálculos triviales.

`CandidateUpdateControls` aplica el mismo criterio a sus opciones derivadas de `Set`, con dependencias explícitas sobre el estado inicial y actual.

## Decisiones backend

La caché implementada es `TTLCache`, en proceso, thread-safe y con copias profundas para que una respuesta no mute la entrada almacenada. El TTL es obligatorio en cada llamada.

| Endpoint | Coste actual | Frecuencia estimada | Cambio de datos | TTL | Clave | Invalidación |
| --- | --- | --- | --- | --- | --- | --- |
| `GET /operations/sales` | Bajo con el stub; será una lectura/agregación de ventas cuando tenga persistencia | Alta en dashboard operativo, varias llamadas por minuto | Por eventos o cierres de venta; no existe escritura en este stub | 30 s | `operations:sales:{user_id}` | No hay endpoint de escritura equivalente todavía; se mantiene aislado por usuario y debe invalidarse al introducir ingestión de ventas |
| `GET /hr/employees` | Bajo con 2 filas; crecerá con el catálogo de empleados | Media/alta al abrir o refrescar dashboard de RRHH | Baja durante la jornada; cambia en actualizaciones administrativas | 30 s | `hr:employees:{user_id}` | `PUT /hr/employees/{employee_id}` limpia el prefijo `hr:employees:` inmediatamente |

La clave siempre incorpora el `user_id` autenticado. No se comparte una respuesta privada entre usuarios. La prueba `services/brasaland-api/tests/test_cache.py` cubre hit, expiración con TTL cero, aislamiento de claves e invalidación por prefijo.

### Inventario de endpoints y decisión

| Método | Ruta | Coste/frecuencia/estabilidad | Decisión |
| --- | --- | --- | --- |
| POST | `/auth/login` | Hash de contraseña; sensible y variable | No cachear |
| GET | `/auth/me` | Lectura privada por sesión | No cachear; depende del usuario y del perfil actual |
| GET/POST | `/users` | Listado puede crecer; writes cambian datos | No cachear mientras no haya invalidación completa para CRUD |
| GET/PUT/DELETE | `/users/{user_id}` | Datos privados y writes frecuentes | No cachear |
| GET/PUT | `/profiles/me` | Datos privados y mutables | No cachear |
| GET | `/operations/sales` | Lectura repetible, alta frecuencia prevista, estable por ventanas | Cachear 30 s por usuario |
| GET | `/operations/inventory` | Lectura operativa que puede cambiar con stock; no se cachea para no ocultar roturas | No cachear |
| GET | `/supply-chain/suppliers` | Catálogo relativamente estable, pero el stub no tiene invalidación de proveedores | No cachear hasta existir una escritura que invalide correctamente |
| POST | `/supply-chain/purchase-orders` | Escritura con efectos operativos | No cachear |
| GET | `/hr/employees` | Lectura repetible y estable dentro de una jornada | Cachear 30 s por usuario |
| PUT | `/hr/employees/{employee_id}` | Escritura que cambia el listado | No cachear; invalida empleados |
| GET | `/health` | Comprobación mínima, barata | No cachear |

## Frescura frente a rendimiento

Se eligieron 30 segundos porque un dashboard operativo puede tolerar que una lectura de ventas o una lista de empleados tarde como máximo una ventana corta en reflejar un cambio, mientras evita repetir la misma lectura en cada refresco. Para empleados, las escrituras invalidan de inmediato, por lo que el TTL solo cubre lecturas sin cambios. Para ventas, el stub no tiene una operación de escritura; cuando se añada ingestión real, esa escritura deberá invalidar `operations:sales:{user_id}` o cambiar la estrategia a una caché por ventana temporal.

No se eligió un TTL largo: datos de inventario, sesión, perfiles, usuarios y auth requieren más frescura o son privados. La caché es una optimización deliberadamente limitada, no una política global.

## Verificación

- `npm run lint`: correcto, con el warning preexistente en `coverage`.
- `npm run build`: correcto con Next.js 16.2.7.
- `uv run pytest -q`: `2 passed`.
- `uv run python -m compileall -q src tests`: correcto.
- Prueba focalizada de TTL, aislamiento e invalidación: correcta.
- Prueba manual de servidor: tres lecturas repetidas por endpoint y escritura de empleado seguida de lectura con salario actualizado.
- Middleware visible: `GET /health -> 200 | 1.8ms`.
