Tu CTO ha registrado el siguiente ticket:

# Ticket: AUTH-088 — Cobertura de pruebas unitarias para la API de autenticación

* **Prioridad:** Alta
* **Contexto:** Tras la regresión de la semana pasada, requerimos pruebas unitarias en todos los endpoints de autenticación antes de fusionar cualquier nuevo cambio.

## Alcance
* La batería de pruebas debe cubrir todos los endpoints de la API de autenticación.
* Cada endpoint debe tener como mínimo: una prueba de camino feliz, una prueba de caso límite y una prueba de modo de fallo.
* Usar `pytest` para el backend en FastAPI y `Jest` para la lógica en TypeScript.
* Las pruebas deben pasar limpiamente con `uv run pytest` y `jest --coverage`.
* No probar la serialización HTTP — probar la lógica.
* **Entregable:** Una batería de pruebas funcional incluida junto al código de la API existente, con un `TESTING.md` breve que explique cómo ejecutarla.

Antes de escribir tu primera prueba, define tu plan de pruebas: lista los casos que quieres cubrir para cada endpoint, identifica los casos límite (campos vacíos, usuarios duplicados, tokens malformados) y piensa qué entradas podrían producir comportamientos inesperados. Luego usa la IA para que te ayude a generar el código de los tests — pero las decisiones sobre qué probar son tuyas.

Este es el tipo de trabajo que distingue a un junior que entrega funcionalidades de un profesional que entrega software fiable.

* Si trabajas en local, asegúrate de haber ejecutado `uv sync` para instalar las dependencias.
* Si usas GitHub Codespaces, reabre tu proyecto existente desde tu perfil de GitHub.

Instala las dependencias de testing si aún no están presentes:

```bash
# Python / FastAPI
uv add --dev pytest pytest-cov httpx

# TypeScript (si aplica)
npm install --save-dev jest @types/jest ts-jest
## Qué debes hacer

### Plan de pruebas

* Crea un archivo `TESTING.md` en la raíz de tu proyecto documentando: cómo ejecutar las pruebas, qué cubre cada suite y qué casos decidiste incluir y por qué.
* Antes de escribir ningún test, lista en `TESTING.md` los casos que planeas cubrir: camino feliz, casos límite y modos de fallo para cada endpoint.

### FastAPI — pytest

* Crea un directorio `tests/` en la raíz de tu proyecto FastAPI.
* Escribe un módulo de pruebas para cada endpoint de autenticación (p. ej., `test_register.py`, `test_login.py`, `test_token.py`).
* Para cada endpoint, implementa como mínimo:
  * Una prueba de camino feliz (entrada válida, respuesta esperada).
  * Una prueba de caso límite (entrada en el límite: campo vacío, usuario duplicado, etc.).
  * Una prueba de modo de fallo (credenciales inválidas, token expirado, solicitud malformada).
* Todas las pruebas deben pasar al ejecutar `uv run pytest` desde la raíz del proyecto.
* Ejecuta `uv run pytest --cov` y comprueba que tu batería alcanza al menos 70% de cobertura en el módulo de autenticación.

### TypeScript — Jest (si tu proyecto incluye lógica de utilidades en TypeScript)

* Configura Jest con un archivo `jest.config.ts` o `jest.config.js` en la raíz de tu proyecto TypeScript.
* Escribe pruebas unitarias para cualquier función de utilidad relacionada con la autenticación (generación de tokens, validación, helpers de hash de contraseñas).
* Para cada función, implementa como mínimo: una prueba de camino feliz y una prueba de modo de fallo.
* Todas las pruebas deben pasar al ejecutar `jest --coverage`.

### Flujo de trabajo asistido por IA

* Usa tu agente de IA para identificar casos de prueba que podrías haber pasado por alto — proporciónale la lógica de tu endpoint y pídele que sugiera casos límite.
* Usa la IA para generar el boilerplate de los tests, pero revisa y entiende cada prueba antes de confirmarla.
* Si un test generado revela un bug en tu código existente, corrígelo y documéntalo en `TESTING.md`.
> ⚠️ **IMPORTANTE:** No pruebes la serialización HTTP ni los internos del framework. Cada test debe afirmar algo sobre la lógica de negocio de tu aplicación — lo que el endpoint decide, no cómo responde.

---

## 🏆 Actividad extra — Cierra el backlog mientras tienes el setup hecho

El CTO marcó AUTH-088 como el bloqueante, pero hay dos tickets que llevan semanas en el backlog sin que nadie los persiga. Son de baja prioridad — nadie los está pidiendo — pero ahora que tienes la infraestructura de testing montada, sería una pena no cerrarlos. Si terminas antes de tiempo, liquídalos.

---

### Ticket: API-042 — Pruebas unitarias para los endpoints del backoffice

* **Prioridad:** Baja
* **Contexto:** La API del backoffice nunca ha tenido batería de pruebas. No se han reportado regresiones, pero probablemente es porque el equipo es pequeño, no porque el código sea sólido. Ahora que tenemos `pytest` configurado, ampliemos la cobertura antes de que el equipo crezca.
* **Alcance:**
  * Elige al menos dos grupos de endpoints del backoffice distintos a la autenticación (p. ej., recursos, usuarios, elementos — lo que tenga el dominio de tu empresa).
  * Aplica la misma estructura de tres niveles: camino feliz, caso límite, modo de fallo.
  * Apunta a un **60% de cobertura** en los módulos que pruebes — el listón es más bajo que en auth, pero sigue siendo significativo.
* **Entregable:** Nuevos módulos de prueba añadidos al directorio `tests/` existente. Actualiza `TESTING.md` con los nuevos resultados de cobertura.

---

### Ticket: FE-019 — Pruebas unitarias para las funciones de utilidad del frontend

* **Prioridad:** Baja
* **Contexto:** El frontend ha ido acumulando funciones de utilidad a lo largo de los hitos anteriores — validadores de formularios, formateadores de datos, manejadores de respuestas de API — que nunca se han probado. Un bug en cualquiera de ellas podría romper la UI de forma silenciosa y difícil de rastrear.
* **Alcance:**
  * Identifica al menos tres funciones de utilidad o *helper* en tu frontend Next.js / TypeScript.
  * Escribe tests de Jest para cada una: una prueba de camino feliz y una de modo de fallo por función.
  * Buenas candidatas: validadores de entrada, formateadores de fechas o monedas, *parsers* de respuestas, helpers de almacenamiento de tokens.
* **Entregable:** Un directorio `__tests__/` dentro de tu proyecto frontend con los archivos de prueba. Actualiza `TESTING.md` con las instrucciones para ejecutar los tests del frontend de forma independiente.

---

### Checklist de extras:

* [ ] (Extra) Escribe tests con `pytest` para al menos dos grupos de endpoints del backoffice, alcanzando un 60% de cobertura en esos módulos.
* [ ] (Extra) Escribe tests de `Jest` para al menos tres funciones de utilidad del frontend (camino feliz + modo de fallo en cada una).
* [ ] (Extra) Actualiza `TESTING.md` con los resultados de cobertura e instrucciones de ejecución para ambas suites adicionales.
## Qué vamos a evaluar

* [ ] Existe un archivo `TESTING.md` que documenta el plan de pruebas, cómo ejecutarlas y los resultados de cobertura.
* [ ] `uv run pytest` se ejecuta sin errores desde la raíz del proyecto y todas las pruebas pasan.
* [ ] La batería incluye pruebas de **camino feliz**, **casos límite** y **modos de fallo** para cada endpoint de autenticación.
* [ ] La cobertura del módulo de autenticación es igual o superior al **70%** (verificada con `uv run pytest --cov`).
* [ ] Las pruebas afirman lógica de negocio, no serialización HTTP ni comportamiento del framework.
* [ ] Si existen funciones de utilidad en TypeScript, los tests de Jest están presentes y pasan.
* [ ] El flujo asistido por IA es evidente: `TESTING.md` menciona al menos un caso identificado con ayuda de la IA o un bug detectado por la batería de pruebas.
* [ ] El código está limpio: los tests tienen nombres claros, siguen una estructura consistente e incluyen comentarios breves que explican las afirmaciones no evidentes.

> **Nota:** La evaluación no requiere un 100% de cobertura. La calidad y el criterio de los casos de prueba importan más que el porcentaje. Un 70% bien razonado vale más que un 95% mecánico.

### Actividad extra
Las baterías de pruebas del backoffice y el frontend no son obligatorias para aprobar, pero se reconocerán en la evaluación si están presentes y pasan.