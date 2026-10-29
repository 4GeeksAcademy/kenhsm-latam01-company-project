# 🚀 Quick Start: Milestone 5

## Configuración Rápida

### 1. Obtener DATABASE_URL

Ve a Supabase:
1. Dashboard → Project Settings → Database
2. Copia la conexión PostgreSQL (con Transaction Pooler recomendado)
3. Formato: `postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres`

### 2. Configurar Variables de Entorno

```bash
# En el directorio services/brasaland-api/
export SECRET_KEY="dev-key-$(openssl rand -hex 16)"
export JWT_ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=30
export PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=15
export OPENAI_API_KEY=sk-test
export QDRANT_URL=http://localhost:6333
export AGENT_QUERY_LIMIT_PER_MINUTE=10
export DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres"
```

### 3. Iniciar API

```bash
cd services/brasaland-api
uv run uvicorn src.brasaland_api.main:app --reload
```

**Debe mostrar:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:root:Inventory database initialized successfully.
```

### 4. Ejecutar Seeding

```bash
cd services/brasaland-api
uv run python -m src.brasaland_api.modules.inventory.seed
```

**Debe crear:**
- 6 Ingredientes
- 4 Entradas
- 3 Salidas

---

## Comandos de Testing

### Verificar API

```bash
# Health check
curl http://localhost:8000/health

# Ver documentación interactiva
open http://localhost:8000/docs
```

### Listar Ingredientes (GET - Público)

```bash
curl http://localhost:8000/inventory/products | jq .
```

**Esperado:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Falda de ternera",
      "sku": "BRS-BEEF-001",
      "current_stock": 60.0,
      ...
    }
  ],
  "total": 6
}
```

### Listar Órdenes (GET - Público)

```bash
curl http://localhost:8000/inventory/orders | jq .
```

### Obtener Token JWT

```bash
# Login (usa credenciales de admin)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin@brasaland.com",
    "password": "password123"
  }' | jq -r .access_token

# Guardar en variable
export TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@brasaland.com","password":"password123"}' \
  | jq -r .access_token)
```

### Crear Ingrediente (POST - Requiere Auth)

```bash
curl -X POST http://localhost:8000/inventory/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nuevo Ingrediente",
    "sku": "BRS-TEST-001",
    "unit": "kg",
    "category": "meat",
    "country": "CO"
  }' | jq .
```

### Registrar Entrada (POST - Requiere Auth)

```bash
curl -X POST http://localhost:8000/inventory/orders/inbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 25,
    "supplier_name": "Test Supplier",
    "location_id": 1
  }' | jq .
```

### Registrar Salida Válida (POST - Requiere Auth)

```bash
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 10,
    "reason": "consumption",
    "location_id": 1
  }' | jq .
```

### Registrar Salida Inválida (POST - Debe retornar 400)

```bash
curl -X POST http://localhost:8000/inventory/orders/outbound \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": 1,
    "quantity": 10000,
    "reason": "consumption",
    "location_id": 1
  }' | jq .

# Esperado: HTTP 400 con mensaje de error
```

---

## Verificar en Supabase

### Conectar a PostgreSQL

```bash
# Desde terminal (si tienes psql)
psql "postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres"

# O usar Supabase SQL Editor en web
```

### Ver Tablas Creadas

```sql
-- Verificar existencia de tablas
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('ingredient', 'ingredient_entry', 'ingredient_exit');

-- Ver estructura
\d ingredient
\d ingredient_entry
\d ingredient_exit

-- Contar registros
SELECT COUNT(*) FROM ingredient;
SELECT COUNT(*) FROM ingredient_entry;
SELECT COUNT(*) FROM ingredient_exit;

-- Ver datos
SELECT id, name, sku, country FROM ingredient;
SELECT * FROM ingredient_entry LIMIT 5;
SELECT * FROM ingredient_exit LIMIT 5;
```

---

## Troubleshooting

### Error: "DATABASE_URL not configured"

```bash
# Verifica que la variable está configurada
echo $DATABASE_URL

# Si está vacía, configúrala
export DATABASE_URL="postgresql://postgres:PASSWORD@HOST:PORT/postgres"
```

### Error: "table 'ingredient' does not exist"

1. Verifica que init_inventory_db() se ejecutó en startup
2. Logs deben mostrar: `INFO:root:Inventory database initialized successfully.`
3. Verifica permisos en Supabase
4. Intenta hacer login en Supabase SQL Editor

### Error: Token JWT inválido

```bash
# Regenera el token
export TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@brasaland.com","password":"password123"}' \
  | jq -r .access_token)

# Verifica que el token está configurado
echo $TOKEN
```

### Error: 500 Internal Server Error

1. Revisa logs de API (terminal donde corre uvicorn)
2. Verifica conexión a Supabase en DATABASE_URL
3. Verifica que el usuario de Supabase tiene permisos

---

## Checklist de Validación

- [ ] API inicia sin errores
- [ ] `GET /health` retorna 200
- [ ] `GET /inventory/products` retorna 6 ingredientes
- [ ] `GET /inventory/orders` retorna entradas y salidas
- [ ] Obtener token JWT funciona
- [ ] `POST /inventory/products` crea ingrediente (con auth)
- [ ] `POST /inventory/orders/inbound` registra entrada (con auth)
- [ ] `POST /inventory/orders/outbound` registra salida (con auth)
- [ ] `POST /inventory/orders/outbound` rechaza stock negativo (HTTP 400)
- [ ] Supabase muestra 6 ingredientes en tabla
- [ ] Supabase muestra 4+ entradas en tabla
- [ ] Supabase muestra 3+ salidas en tabla
- [ ] OpenAPI spec en `/docs` muestra 6 endpoints

---

## Documentación Completa

Consulta para más detalles:
- **MILESTONE5-DELIVERY.md** — Resumen técnico
- **MILESTONE5-TESTING.md** — Guía de testing (7 fases)
- **MILESTONE5-INDEX.md** — Índice de archivos
- **services/.../README.md** — Documentación del módulo

---

## URLs Útiles

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Supabase Dashboard: https://app.supabase.com

---

**¿Necesitas ayuda?** Revisa MILESTONE5-TESTING.md para guía completa

