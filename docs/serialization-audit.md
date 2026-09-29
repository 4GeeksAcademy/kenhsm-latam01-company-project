# Auditoria de serializacion de la API

Fecha: 2026-09-27
Aplicacion: `services/brasaland-api`

## Criterio

Se considera serializado cuando la ruta declara un `response_model` explicito. Los esquemas de entrada son independientes de los de salida. Las respuestas no incluyen `hashed_password`, tokens internos ni claves relacionales que el consumidor no necesita.

## Inventario de endpoints

| Metodo | Ruta | Proposito | Estado original | Problema / causa | Contrato final |
| --- | --- | --- | --- | --- | --- |
| GET | `/health` | Health check | Parcial | Retornaba `dict` generico sin esquema | `HealthOut`: `status` |
| POST | `/auth/login` | Emitir JWT | ✅ Ya serializado | `Token` explicito; el token es el resultado publico esperado del login | `Token`: `access_token`, `token_type` |
| GET | `/auth/me` | Perfil del usuario autenticado | ✅ Ya serializado | `CurrentUserOut` explicito; email permitido solo para el propio llamante | `CurrentUserOut`: `email`, `role`, `profile` |
| POST | `/users` | Registrar usuario | ⚠️ Parcialmente serializado | Reutilizaba `UserOut` y reenviaba email en un flujo publico; el input contiene password pero la salida no debe repetir credenciales | `UserRegistrationOut`: `id`, `is_active`, `role`, `created_at` |
| GET | `/users` | Listar usuarios | ✅ Ya serializado | Proyeccion segura explicita; no devuelve password ni relaciones | `list[UserOut]` |
| GET | `/users/{user_id}` | Ver usuario | ✅ Ya serializado | Proyeccion segura explicita | `UserOut` |
| PUT | `/users/{user_id}` | Actualizar email/rol | ✅ Ya serializado | `UserUpdate` separado de `UserOut`; salida filtrada | `UserOut` |
| DELETE | `/users/{user_id}` | Eliminar usuario | ⚠️ Parcialmente serializado | No tenia `response_model` explicito; respuesta 204 no tiene cuerpo | `response_model=None`, status 204 |
| GET | `/profiles/me` | Obtener perfil propio | ⚠️ Parcialmente serializado | `ProfileOut` incluia `user_id`, una FK interna innecesaria para una ruta `/me` | `ProfileOut`: `id`, `name`, `phone`, `address` |
| PUT | `/profiles/me` | Actualizar perfil propio | ✅ Ya serializado | `ProfileUpdate` separado; salida con la misma proyeccion segura | `ProfileOut` |
| GET | `/operations/sales` | Listar resumen de ventas | ❌ Sin serializar | Retornaba `list[dict]`, sin contrato | `list[SalesSummary]`: `location_id`, `date`, `total_usd` |
| GET | `/operations/inventory` | Listar inventario | ❌ Sin serializar | Retornaba `list[dict]`, sin contrato | `list[InventoryItem]`: `location_id`, `ingredient`, `quantity` |
| GET | `/supply-chain/suppliers` | Listar proveedores | ❌ Sin serializar | Retornaba `list[dict]`, sin contrato | `list[SupplierOut]`: `id`, `name`, `country` |
| POST | `/supply-chain/purchase-orders` | Crear pedido de compra | ❌ Sin serializar | El retorno incluia `created_by`, una FK interna no necesaria para el consumidor | Input `PurchaseOrderCreate`; salida `PurchaseOrderOut`: input + `id`, `created_at` |
| GET | `/hr/employees` | Listar empleados | ❌ Sin serializar | Retornaba `list[dict]`; el salario se mantiene explicito porque el dashboard interno lo necesita | `list[EmployeeOut]`: `id`, `name`, `location_id`, `salary_usd` |
| PUT | `/hr/employees/{employee_id}` | Actualizar datos operativos del empleado | ❌ Sin serializar | Retornaba el diccionario mutable directamente | Input `EmployeeUpdate`; salida `EmployeeOut` |

Estado final: **16/16 endpoints con contrato de respuesta explicito**. Para el DELETE 204, `response_model=None` es intencional porque no existe cuerpo de respuesta.

## Decisiones de seguridad y payload

- `UserCreate` y `UserUpdate` solo son esquemas de entrada. Ningun esquema de salida contiene `hashed_password`.
- `POST /users` usa una respuesta especifica de registro sin email: el cliente solo necesita confirmar la identidad creada y su estado; el email ya fue enviado en la solicitud.
- `POST /auth/login` devuelve `access_token` porque es el producto publico de esa operacion. No devuelve el objeto usuario ni campos de credenciales.
- `GET /auth/me` es la unica proyeccion que devuelve el email, limitado al usuario autenticado, porque la vista de perfil lo necesita.
- `ProfileOut` aplana el perfil y omite `user_id`: la ruta ya fija el usuario a `/me` y no necesita anidado ni FK en bruto.
- `PurchaseOrderOut` omite `created_by`: el backend lo conserva para control interno, pero el consumidor no necesita esa relacion en la confirmacion.
- Los listados devuelven proyecciones planas y no objetos ORM/modelo completos.

## Verificacion

- `uv run python -m compileall -q src`
- Suite existente: `uv run pytest -q` (no habia tests registrados antes de esta auditoria).
- OpenAPI generado: 16 endpoints, todos con esquema de respuesta; `hashed_password` no aparece en componentes.
- `GET /docs`: HTTP 200.
- `GET /health`: `{"status":"ok"}`.
- `POST /users`: respuesta sin email, password ni `hashed_password`.
- `GET /operations/sales` sin token: HTTP 401.
- Pruebas de contrato añadidas en `services/brasaland-api/tests/test_serialization.py`.
