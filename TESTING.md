# Testing

## Plan de pruebas

La suite de backend prueba la lógica de negocio llamando a funciones y routers directamente, sin convertir las pruebas en una validación de serialización HTTP.

### AUTH-088: autenticación

| Superficie | Camino feliz | Caso límite | Modo de fallo |
| --- | --- | --- | --- |
| Registro de usuario (`users`) | Crea usuario y perfil vinculado | Contraseña vacía o menor de 8 caracteres | Email duplicado |
| Login (`auth.login`) | Credenciales válidas generan token | Contraseña vacía | Email inexistente, contraseña incorrecta y usuario inactivo |
| Usuario actual (`auth.me`) | Token válido resuelve usuario y perfil | Usuario válido sin perfil | Token malformado, expirado, sin `sub` o usuario inactivo |
| Seguridad JWT | Token creado se puede decodificar | Expiración configurable | Token expirado o firmado con una clave incorrecta |
| Contraseñas | Hash verifica la contraseña original | Contraseña vacía | Contraseña incorrecta |

La cobertura objetivo para los módulos de autenticación es como mínimo 70%. La batería incluye un caso de token expirado porque fue el origen de la regresión descrita en el contexto, y casos de contraseña vacía, usuario duplicado y token sin `sub` porque cruzan límites frecuentes de validación.

### API-042: backoffice

Se cubrirán los grupos `operations` y `supply-chain` con camino feliz, entradas límite y fallos de autenticación o validación. El objetivo es al menos 60% en los módulos probados.

### FE-019: utilidades TypeScript

Se probarán `parseJsonResponse`, `getStoredToken`/`setStoredToken`/`clearStoredToken` y `authenticatedFetch`. Cada utilidad tendrá camino feliz y fallo relevante, incluyendo respuestas no OK, ausencia de `window`, token ausente y respuesta `401`.

## Ejecución

### Backend

Desde `services/brasaland-api`:

```bash
uv sync
uv run pytest
uv run pytest --cov=brasaland_api.modules.auth --cov=brasaland_api.core.security --cov-report=term-missing
```

### Frontend

Desde `apps/talent-pipeline-tracker`:

```bash
npm install
npx jest --coverage
```

## Asistencia de IA y decisiones

Se usó un agente explorador para revisar las rutas de autenticación, localizar los helpers reutilizables y sugerir casos límite. Las decisiones finales fueron revisar explícitamente expiración JWT, tokens malformados, ausencia de `sub`, usuarios duplicados y respuestas `401`; no se aceptaron pruebas que solo afirmaran detalles de serialización del framework.

## Resultados

- AUTH-088: `28 passed`; autenticación y seguridad JWT: **100%** de cobertura.
- API-042: `6 passed`; `operations` y `supply_chain`: **100%** de cobertura.
- FE-019: `5 passed`; helpers TypeScript: **86.84%** de líneas y **76.92%** de ramas.