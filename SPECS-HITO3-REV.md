# El reto



El departamento de People & Talent de tu empresa está en medio de una campaña de selección activa. La posición abierta ha recibido más de 100 candidaturas en menos de dos semanas y el equipo está desbordado: llevan el seguimiento de los candidatos en una hoja de cálculo compartida, escriben las notas de las entrevistas en documentos separados y actualizan los estados manualmente por hilos de correo. El proceso se está desmoronando.

El equipo de Tecnología ya ha construido y expuesto una API REST para gestionar el pipeline de candidaturas. Tu trabajo es construir el frontend que el equipo de People empezará a usar el lunes.

El sistema debe permitir:

- Ver todas las candidaturas de un vistazo.
- Filtrarlas por estado y por etapa.
- Acceder al detalle de cada candidatura sin perder el contexto del listado.

La responsable de People ha compartido lo que necesitan con urgencia.

---

# Lo que la herramienta debe hacer

1. Mostrar todas las candidaturas en un listado:
   - Nombre.
   - Puesto.
   - Estado actual.
   - Etapa actual.

2. Permitir:
   - Filtrar por estado.
   - Filtrar por etapa.
   - Buscar por nombre o email.

   Todo ello sin recargar la página.

3. Abrir la vista de detalle de un candidato y, desde ahí, cambiar su estado o etapa con una sola interacción.

4. Añadir notas internas a una candidatura y eliminarlas cuando ya no sean relevantes.

5. Registrar nuevas candidaturas directamente desde la interfaz y editar los datos de una candidatura cuando sea necesario corregir información.

---

La API ya está lista y está documentada en:

👉 https://playground.4geeks.com/tracker/api/v1/docs

Todas las peticiones deben gestionarse de forma asíncrona. La interfaz debe:

- Comunicar claramente los estados de carga.
- Manejar errores de forma visible.
- Evitar fallos silenciosos.
- Informar siempre al usuario de lo que está ocurriendo.

Esta es una herramienta interna real que va a usar gente real desde el primer día. **Constrúyela como tal.**

---

# 🌱 Cómo iniciar el proyecto

Este hito forma parte del monorepo del curso. No necesitas clonar ningún repositorio nuevo, el tuyo ya existe.

1. Abre el monorepo en el que has trabajado durante el curso en **GitHub Codespaces** o clónalo localmente si prefieres trabajar en tu máquina.

2. Navega a la carpeta `/uis` y crea el directorio para este hito:

```text
/uis/talent-pipeline-tracker/
```

3. Inicializa un proyecto Next.js con TypeScript dentro de esa carpeta:

```bash
cd uis/talent-pipeline-tracker

npx create-next-app@latest . --typescript --app --tailwind --eslint
```

4. Crea un archivo `.env.local` en la raíz de la aplicación con la URL base de la API:

```env
NEXT_PUBLIC_API_URL=https://playground.4geeks.com/tracker/api/v1
```

5. Instala las dependencias:

```bash
npm install
```

6. Arranca el servidor de desarrollo:

```bash
npm run dev
```
# 🖥️ Qué debes hacer

## Vistas y navegación

- Crea una página de listado de candidaturas (`/`) que muestre todos los candidatos obtenidos desde:

  ```http
  GET /records
  ```

- Crea una página de detalle de candidatura (`/candidates/[id]`) que obtenga y muestre los datos completos desde:

  ```http
  GET /records/:id
  ```

- La navegación entre listado y detalle debe usar el sistema de rutas de Next.js, sin recargas completas de página.

---

## Listado de candidaturas

- Muestra el nombre completo, el puesto, el estado actual y la etapa actual de cada candidato.
- Implementa filtro por estado y filtro por etapa usando query parameters (`useSearchParams`).
- Implementa un campo de búsqueda que filtre por nombre o email sin recargar la página.
- Muestra un estado de carga mientras se obtienen los datos y un mensaje de error si la petición falla.

---

## Detalle de candidatura

- Muestra todos los campos disponibles:
  - Nombre
  - Email
  - Teléfono
  - Puesto
  - LinkedIn
  - Enlace al CV
  - Años de experiencia
  - Estado
  - Etapa
  - Fecha de aplicación

- Incluye un control para actualizar el estado mediante:

  ```http
  PATCH /records/:id
  ```

- Incluye un control para actualizar la etapa mediante:

  ```http
  PATCH /records/:id
  ```

- Muestra el listado de notas obtenidas desde:

  ```http
  GET /records/:id/notes
  ```

- Permite añadir una nueva nota mediante:

  ```http
  POST /records/:id/notes
  ```

- Permite eliminar una nota mediante:

  ```http
  DELETE /records/:id/notes/:note_id
  ```

---

## Gestión de candidaturas

- Incluye un formulario para registrar una nueva candidatura:

  ```http
  POST /records
  ```

- Incluye un formulario para editar los datos de una candidatura:

  ```http
  PUT /records/:id
  ```

- Ambos formularios deben validar los campos requeridos antes de enviarse.
- Muestra feedback de éxito o error tras cada envío.

---

## Estado y manejo asíncrono

- Todas las llamadas a la API deben gestionarse con:

  ```typescript
  async/await
  ```

- Cada operación de obtención de datos debe tener al menos tres estados en la UI:
  - Cargando
  - Éxito
  - Error

- Tras un `PATCH`, `PUT` o `POST`, actualiza la interfaz para reflejar el cambio sin requerir una recarga completa de página.

---

## Estructura del código

- Organiza el proyecto con una estructura de carpetas clara:

  ```text
  /components
  /hooks      (si aplica)
  /types
  /lib
  /services
  ```

- Define tipos TypeScript para todas las estructuras de datos recibidas de la API.

> ⚠️ **IMPORTANTE:** Los nombres de campos, etiquetas visibles, estados y valores específicos del dominio en tu implementación deben coincidir con lo especificado en tu `CONTEXT-HITO3-REV.md`.
>
> Por ejemplo, si tu empresa es **TrackFlow**, la interfaz debe sentirse como una herramienta interna del equipo de People & Talent de TrackFlow, aunque los nombres de campos de la API sigan siendo los definidos por el tracker backend.
>
> Una implementación genérica que ignore el contexto de tu empresa no será aceptada.

> ⚠️ **IMPORTANTE:** Usa únicamente **Next.js (App Router)**, **React** y **TypeScript**.
>
> No uses librerías externas de gestión de estado (**Redux**, **Zustand**, **Jotai**, etc.). El estado a nivel de componente con hooks es suficiente para este hito.

---

# ✅ Qué vamos a evaluar

- La página de listado renderiza correctamente los datos obtenidos de la API.
- Los filtros por estado y etapa funcionan usando query parameters sin recargas de página.
- La búsqueda por nombre o email funciona sin recargar la página.
- La página de detalle carga y muestra todos los campos del candidato correcto por ID.
- El estado y la etapa se pueden actualizar desde el detalle usando:

  ```http
  PATCH
  ```

- Las notas se pueden listar, añadir y eliminar desde el detalle.
- Las nuevas candidaturas se pueden registrar mediante un formulario usando:

  ```http
  POST
  ```

- Los datos de una candidatura existente se pueden editar mediante un formulario usando:

  ```http
  PUT
  ```

- Los estados de carga, éxito y error son visibles para el usuario en todas las operaciones asíncronas.
- Los tipos TypeScript están definidos y se usan para las estructuras de datos de la API.
- La estructura de carpetas separa componentes, tipos y lógica de acceso a datos.
- El App Router de Next.js se usa correctamente para navegación y rutas dinámicas.
- No hay prop drilling: el estado está correctamente acotado a nivel de componente.
- La implementación refleja el contexto de la empresa asignada (nombres de campo, etiquetas y valores del dominio).

---

> **Nota:** El diseño visual y el estilado no se evaluarán formalmente en este hito, pero la interfaz debe ser usable y mostrar toda la información requerida con claridad.