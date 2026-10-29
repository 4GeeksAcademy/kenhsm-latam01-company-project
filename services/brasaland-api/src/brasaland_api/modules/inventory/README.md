# 📦 Inventory Management Module

**Brasaland Digital — Gestión Centralizada de Inventario**

Este módulo implementa la gestión centralizada de inventario de Brasaland. Los ingredientes, entregas y consumos se persisten en Supabase (PostgreSQL) mediante SQLModel ORM, mientras que la autenticación continúa siendo gestionada por TinyDB.

---

## 🎯 Características Principales

✅ **Doble Base de Datos**
- TinyDB: Autenticación y usuarios (existente)
- Supabase PostgreSQL: Ingredientes, órdenes de entrada y salida (nuevo)

✅ **Regla de Negocio: Stock de Solo Lectura**
- El stock nunca se modifica directamente
- Solo se modifica a través de órdenes de entrada (entregas) y salida (consumo/merma)
- Stock = SUM(IngredientEntry) - SUM(IngredientExit)

✅ **Validación de Inventario**
- No se puede registrar una salida que resulte en stock negativo
- Se rechaza con HTTP 400 antes de persistir

✅ **Auditoría**
- Cada orden almacena el UUID del usuario que la creó
- Timestamps auto-generados en creación

---

## 📊 Entidades

### Ingredient (Ingrediente)

Representa un producto en el inventario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | PK autoincremental |
| `name` | str | Nombre del ingrediente (ej. "Falda de ternera") |
| `sku` | str | Código único (ej. "BRS-BEEF-001") |
| `unit` | str | Unidad de medida ("kg", "litro", "unidad") |
| `category` | str | Categoría ("meat", "produce", "sauce", "beverage", "packaging", "cleaning") |
| `country` | str | "CO" o "US" |
| `current_stock` | float | **CALCULADO** — SUM(entries) - SUM(exits) |

### IngredientEntry (Entrega de Proveedor)

Representa una entrega de ingredientes que aumenta el stock.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | PK autoincremental |
| `ingredient_id` | int | FK → Ingredient |
| `quantity` | float | Cantidad recibida |
| `supplier_name` | str | Nombre del proveedor |
| `location_id` | int | Local receptor (1-14) |
| `created_at` | datetime | Auto-generado |
| `user_uuid` | str | UUID del supervisor que registró |

### IngredientExit (Consumo o Merma)

Representa una reducción de stock por consumo o merma.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | PK autoincremental |
| `ingredient_id` | int | FK → Ingredient |
| `quantity` | float | Cantidad consumida/mermada |
| `reason` | str | "consumption" o "waste" |
| `location_id` | int | Local donde ocurrió (1-14) |
| `created_at` | datetime | Auto-generado |
| `user_uuid` | str | UUID del personal que registró |

---

## 🔗 API Endpoints

Todos bajo el prefijo `/inventory`.

### GET `/inventory/products`
Lista todos los ingredientes con su stock actual calculado.

**Respuesta:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Falda de ternera",
      "sku": "BRS-BEEF-001",
      "unit": "kg",
      "category": "meat",
      "country": "CO",
      "current_stock": 60.0
    }
  ],
  "total": 6
}
```

### POST `/inventory/products`
Crea un nuevo ingrediente. **Requiere autenticación.**

**Body:**
```json
{
  "name": "Nuevo Ingrediente",
  "sku": "BRS-NEW-001",
  "unit": "kg",
  "category": "meat",
  "country": "CO"
}
```

**Respuesta:** 201 Created con el ingrediente creado (stock inicial = 0).

### GET `/inventory/products/{id}`
Obtiene un ingrediente individual con su stock actual.

**Respuesta:** 200 OK con el objeto Ingredient completo.

---

### POST `/inventory/orders/inbound`
Registra una entrega de proveedor (aumenta stock). **Requiere autenticación.**

**Body:**
```json
{
  "ingredient_id": 1,
  "quantity": 50.0,
  "supplier_name": "Carnes del Valle S.A.",
  "location_id": 3
}
```

**Respuesta:** 201 Created con los detalles de la entrada y el ingrediente con stock actualizado.

### POST `/inventory/orders/outbound`
Registra una salida (consumo o merma). **Requiere autenticación.**

**Validación:** Si la salida resultaría en stock negativo, se rechaza con HTTP 400.

**Body:**
```json
{
  "ingredient_id": 1,
  "quantity": 15.0,
  "reason": "consumption",
  "location_id": 1
}
```

**Respuesta:** 201 Created con los detalles de la salida, o HTTP 400 si hay stock insuficiente.

### GET `/inventory/orders`
Lista todas las entradas y salidas.

**Respuesta:**
```json
{
  "entries": [...],
  "exits": [...]
}
```

---

## 🚀 Instalación y Uso

### 1. Configurar Variables de Entorno

En `.env`:
```bash
DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[database]
```

La cadena de conexión debe apuntar a Supabase (con Transaction Pooler).

### 2. Ejecutar Migraciones

El esquema se crea automáticamente al iniciar la aplicación gracias a `SQLModel.metadata.create_all()` en `startup_event()`.

### 3. Sembrar Datos Iniciales

```bash
cd services/brasaland-api
python -m brasaland_api.modules.inventory.seed
```

Esto carga los 6 ingredientes mínimos y las órdenes de prueba.

### 4. Iniciar la API

```bash
uvicorn src.brasaland_api.main:app --reload
```

Accede a la documentación interactiva en: `http://localhost:8000/docs`

---

## 🔐 Autenticación

**Endpoints de lectura (`GET`):**
- Públicos (sin autenticación requerida) según BRIEFING.md.

**Endpoints de escritura (`POST`):**
- Requieren autenticación (token JWT en header `Authorization: Bearer <token>`).
- El UUID del usuario autenticado se extrae de TinyDB y se almacena en la orden.

---

## 🛡️ Reglas de Negocio Implementadas

1. ✅ **Stock Calculado**
   - `current_stock = SUM(IngredientEntry.quantity) - SUM(IngredientExit.quantity)`
   - Nunca se almacena ni se modifica directamente.

2. ✅ **Prevención de Stock Negativo**
   - Una salida que resultaría en stock < 0 se rechaza con HTTP 400.
   - Mensaje: "Insufficient stock for ingredient '{name}'. Available: {available}, requested: {requested}."

3. ✅ **Sin Tabla de Usuarios en Supabase**
   - `user_uuid` es un string que referencia usuarios de TinyDB.
   - No hay replicación de tabla de usuarios.

4. ✅ **Auditoría**
   - Cada orden registra `user_uuid` del creador.
   - Cada orden tiene `created_at` auto-generado.

---

## 📁 Estructura de Archivos

```
services/brasaland-api/src/brasaland_api/modules/inventory/
├── __init__.py          # Exports públicos del módulo
├── models.py            # SQLModel ORM (Ingredient, IngredientEntry, IngredientExit)
├── schemas.py           # Schemas Pydantic (separados de modelos ORM)
├── router.py            # APIRouter con todos los endpoints
└── seed.py              # Script de seeding
```

---

## 🧪 Testing

Vea los endpoints activos en Swagger:
```
GET http://localhost:8000/docs
```

Ejemplo con curl:

```bash
# Listar ingredientes
curl http://localhost:8000/inventory/products

# Crear un ingrediente (requiere auth)
curl -X POST http://localhost:8000/inventory/products \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Nuevo", "sku":"SKU-001", "unit":"kg", "category":"meat", "country":"CO"}'

# Registrar entrada (requiere auth)
curl -X POST http://localhost:8000/inventory/orders/inbound \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id":1, "quantity":50, "supplier_name":"Supplier", "location_id":1}'

# Registrar salida (requiere auth)
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id":1, "quantity":15, "reason":"consumption", "location_id":1}'
```

---

## ⚠️ Consideraciones de Producción

- **Migraciones**: En producción, usa Alembic en lugar de `create_all()`.
- **Índices**: Considera agregar índices en `ingredient_id` y `created_at`.
- **Timestamps UTC**: Todos los `created_at` están en UTC.
- **Transacciones**: SQLModel maneja automáticamente transacciones por sesión.

---

## 📞 Contacto

Para preguntas o problemas, consulte la documentación de:
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Supabase PostgreSQL](https://supabase.com/docs/)

---

**Última actualización:** 2026-10-29  
**Versión:** 1.0.0  
