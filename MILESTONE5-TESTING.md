# 🧪 Milestone 5 Testing Guide

**Objetivo:** Validar que el módulo de inventario funciona correctamente con Supabase real.

---

## Prerequisitos

1. **Supabase Credentials:**
   - URL de proyecto Supabase
   - API Key (o credenciales de conexión PostgreSQL)
   - Transaction Pooler (recomendado para pooling de conexiones)

2. **Configuración de .env:**
   ```bash
   # Formato: postgresql://[user]:[password]@[host]:[port]/[database]
   DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres
   ```

3. **Variables de Entorno Requeridas:**
   ```bash
   SECRET_KEY=<generar con openssl rand -hex 32>
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=15
   OPENAI_API_KEY=sk-...
   QDRANT_URL=http://localhost:6333
   AGENT_QUERY_LIMIT_PER_MINUTE=10
   ```

---

## Fase 1: Inicialización de Base de Datos

### 1.1 Iniciar API

```bash
cd services/brasaland-api
uv run uvicorn src.brasaland_api.main:app --reload
```

**Logs esperados:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:root:Inventory database initialized successfully.
```

### 1.2 Verificar Tablas Creadas

Accede a Supabase SQL Editor y ejecuta:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('ingredient', 'ingredient_entry', 'ingredient_exit');
```

**Resultado esperado:**
```
ingredient
ingredient_entry
ingredient_exit
```

### 1.3 Verificar Estructura de Tablas

```sql
\d ingredient
\d ingredient_entry
\d ingredient_exit
```

Verificar que todas las columnas están presentes según BRIEFING.md

---

## Fase 2: Seeding de Datos

### 2.1 Ejecutar Seeding

```bash
cd services/brasaland-api
uv run python -m src.brasaland_api.modules.inventory.seed
```

**Logs esperados:**
```
✓ Database seeded with 6 ingredients
✓ Created 4 ingredient entries
✓ Created 3 ingredient exits
✓ Stock summary:
  BRS-BEEF-001: 60.0 kg (80 - 20)
  BRS-PORK-001: 42.0 kg (50 - 8)
  ...
```

### 2.2 Verificar Datos en Supabase

```sql
SELECT id, name, sku, country, current_stock FROM ingredient;
```

Verificar que hay 6 ingredientes.

```sql
SELECT COUNT(*) FROM ingredient_entry;  -- Debe ser 4
SELECT COUNT(*) FROM ingredient_exit;   -- Debe ser 3
```

---

## Fase 3: Testing de Endpoints (Sin Autenticación)

### 3.1 Listar Ingredientes (GET /inventory/products)

```bash
curl -s http://localhost:8000/inventory/products | jq .
```

**Respuesta esperada:**
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
    // ... más ingredientes
  ],
  "total": 6
}
```

✅ Verificar:
- [ ] `total` es 6
- [ ] Todos los `current_stock` son positivos
- [ ] Campos `country` están presentes

### 3.2 Obtener Ingrediente Individual (GET /inventory/products/{id})

```bash
curl -s http://localhost:8000/inventory/products/1 | jq .
```

**Respuesta esperada:**
```json
{
  "id": 1,
  "name": "Falda de ternera",
  "sku": "BRS-BEEF-001",
  "unit": "kg",
  "category": "meat",
  "country": "CO",
  "current_stock": 60.0
}
```

✅ Verificar:
- [ ] Status code es 200
- [ ] Todos los campos están presentes
- [ ] `current_stock` coincide con esperado (80 - 20 = 60)

### 3.3 Listar Órdenes (GET /inventory/orders)

```bash
curl -s http://localhost:8000/inventory/orders | jq .
```

**Respuesta esperada:**
```json
{
  "entries": [
    {
      "id": 1,
      "ingredient_id": 1,
      "quantity": 50.0,
      "supplier_name": "Carnes del Valle S.A.",
      "location_id": 3,
      "created_at": "2025-10-20T10:30:00",
      "user_uuid": "...",
      "ingredient": { ... }
    }
    // ... más entradas
  ],
  "exits": [
    {
      "id": 1,
      "ingredient_id": 1,
      "quantity": 15.0,
      "reason": "consumption",
      "location_id": 1,
      "created_at": "2025-10-21T14:00:00",
      "user_uuid": "...",
      "ingredient": { ... }
    }
    // ... más salidas
  ]
}
```

✅ Verificar:
- [ ] `entries` contiene 4 registros
- [ ] `exits` contiene 3 registros
- [ ] Cada salida tiene `reason` válido ("consumption" o "waste")
- [ ] El campo `ingredient` está poblado (sin N+1 queries)

---

## Fase 4: Testing de Endpoints (Con Autenticación)

### 4.1 Obtener Token JWT

Primero, crear un usuario o usar uno existente:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@brasaland.com",
    "password": "password123"
  }'
```

**Respuesta:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

Guardar el token en variable:
```bash
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."
```

### 4.2 Crear Ingrediente (POST /inventory/products)

```bash
curl -X POST http://localhost:8000/inventory/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nuevo Ingrediente",
    "sku": "BRS-NEW-001",
    "unit": "kg",
    "category": "meat",
    "country": "CO"
  }'
```

**Respuesta esperada:** 201 Created
```json
{
  "id": 7,
  "name": "Nuevo Ingrediente",
  "sku": "BRS-NEW-001",
  "unit": "kg",
  "category": "meat",
  "country": "CO",
  "current_stock": 0.0
}
```

✅ Verificar:
- [ ] Status code es 201
- [ ] `current_stock` es 0.0 (sin entradas)
- [ ] En Supabase: `SELECT * FROM ingredient WHERE sku='BRS-NEW-001'` retorna el registro

### 4.3 Registrar Entrada (POST /inventory/orders/inbound)

```bash
curl -X POST http://localhost:8000/inventory/orders/inbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 25.0,
    "supplier_name": "Test Supplier",
    "location_id": 5
  }'
```

**Respuesta esperada:** 201 Created
```json
{
  "id": 5,
  "ingredient_id": 1,
  "quantity": 25.0,
  "supplier_name": "Test Supplier",
  "location_id": 5,
  "created_at": "2025-10-22T09:00:00",
  "user_uuid": "...",
  "ingredient": {
    "id": 1,
    "name": "Falda de ternera",
    "sku": "BRS-BEEF-001",
    "unit": "kg",
    "category": "meat",
    "country": "CO",
    "current_stock": 85.0  // 60 + 25
  }
}
```

✅ Verificar:
- [ ] Status code es 201
- [ ] `current_stock` ha aumentado (60 + 25 = 85)
- [ ] En Supabase: `SELECT SUM(quantity) FROM ingredient_entry WHERE ingredient_id=1` = 105

### 4.4 Registrar Salida Válida (POST /inventory/orders/outbound)

```bash
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 10.0,
    "reason": "consumption",
    "location_id": 2
  }'
```

**Respuesta esperada:** 201 Created
```json
{
  "id": 4,
  "ingredient_id": 1,
  "quantity": 10.0,
  "reason": "consumption",
  "location_id": 2,
  "created_at": "2025-10-22T09:05:00",
  "user_uuid": "...",
  "ingredient": {
    "id": 1,
    "name": "Falda de ternera",
    "sku": "BRS-BEEF-001",
    "unit": "kg",
    "category": "meat",
    "country": "CO",
    "current_stock": 75.0  // 85 - 10
  }
}
```

✅ Verificar:
- [ ] Status code es 201
- [ ] `current_stock` ha disminuido correctamente
- [ ] `reason` es exactamente "consumption"

### 4.5 Registrar Salida Inválida (Stock Negativo)

```bash
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 1000.0,
    "reason": "consumption",
    "location_id": 1
  }'
```

**Respuesta esperada:** 400 Bad Request
```json
{
  "detail": "Insufficient stock for ingredient 'Falda de ternera'. Available: 75, requested: 1000."
}
```

✅ Verificar:
- [ ] Status code es 400 (no 500)
- [ ] Mensaje de error es exacto según BRIEFING
- [ ] En Supabase: `ingredient_exit` NO contiene este registro (validación pre-persistencia)

### 4.6 Validación de `reason`

Intentar con `reason` inválido:

```bash
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 5.0,
    "reason": "invalid_reason",
    "location_id": 1
  }'
```

**Respuesta esperada:** 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "reason"],
      "msg": "Input should be 'consumption' or 'waste'..."
    }
  ]
}
```

✅ Verificar:
- [ ] Status code es 422
- [ ] Solo acepta "consumption" o "waste"

---

## Fase 5: Validación de Permisos

### 5.1 Sin Token

```bash
curl -X POST http://localhost:8000/inventory/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","sku":"SKU","unit":"kg","category":"meat","country":"CO"}'
```

**Respuesta esperada:** 403 Forbidden o 401 Unauthorized
```json
{
  "detail": "No se pudo validar las credenciales."
}
```

✅ Verificar:
- [ ] No permite POST sin token
- [ ] GET /inventory/products sigue siendo público (200)

---

## Fase 6: Performance & Validación de N+1

### 6.1 Medir tiempo de respuesta

```bash
time curl -s http://localhost:8000/inventory/orders | jq . > /dev/null
```

**Esperado:** < 500ms con datos semilla

### 6.2 Verificar Query Logs (SQLAlchemy echo)

Si se habilita echo en db.py:
```python
_sqlmodel_engine = create_engine(..., echo=True)
```

Verificar que para `GET /inventory/orders`:
- [ ] No hay N+1 queries (1 query para ingredientes, 1 para entradas, 1 para salidas)
- [ ] Se usan JOINs o eager loading

---

## Fase 7: Swagger UI

Acceder a:
```
http://localhost:8000/docs
```

✅ Verificar:
- [ ] Todos los 6 endpoints están listados bajo `/inventory`
- [ ] Los parámetros de request/response están documentados
- [ ] Se pueden hacer requests desde Swagger UI

---

## Checklist Final

- [ ] Tablas creadas correctamente en Supabase
- [ ] Seeding completado (6 ingredientes, 4 entradas, 3 salidas)
- [ ] GET /inventory/products retorna stock calculado
- [ ] GET /inventory/products/{id} funciona
- [ ] GET /inventory/orders retorna entradas + salidas
- [ ] POST /inventory/products (con auth) crea ingrediente
- [ ] POST /inventory/orders/inbound (con auth) registra entrada
- [ ] POST /inventory/orders/outbound (con auth) registra salida válida
- [ ] POST /inventory/orders/outbound (stock negativo) rechaza con HTTP 400
- [ ] POST sin token retorna 401
- [ ] Swagger UI documenta todos los endpoints
- [ ] Sin N+1 queries en listados

---

## Troubleshooting

### Error: "DATABASE_URL not configured"

```bash
export DATABASE_URL="postgresql://..."
```

### Error: "table 'ingredient' does not exist"

La inicialización de DB falló. Verificar:
1. DATABASE_URL es válido
2. Permiso de creación de tablas en Supabase
3. Logs de startup: `INFO:root:Inventory database initialized successfully.`

### Error: 500 Internal Server Error en POST

Verificar en logs si hay:
- Validación de FK fallando
- Stock calculado incorrecto
- Transacción fallando

### Error: Token JWT inválido

Regenerar token:
```bash
curl -X POST http://localhost:8000/auth/login ...
```

Verificar que `SECRET_KEY` en .env coincide entre requests.

---

## Referencia Rápida de Comandos

```bash
# Iniciar API
cd services/brasaland-api && uv run uvicorn src.brasaland_api.main:app --reload

# Seed
uv run python -m src.brasaland_api.modules.inventory.seed

# Test GET
curl http://localhost:8000/inventory/products

# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d '{"username":"admin@brasaland.com","password":"..."}' | jq -r .access_token)

# Test POST inbound
curl -X POST http://localhost:8000/inventory/orders/inbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id":1,"quantity":50,"supplier_name":"Test","location_id":1}'

# Test POST outbound (valid)
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id":1,"quantity":10,"reason":"consumption","location_id":1}'

# Test POST outbound (invalid - should return 400)
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id":1,"quantity":10000,"reason":"consumption","location_id":1}'
```

---

**Estado:** Listo para testing  
**Última actualización:** 2025-01-22

