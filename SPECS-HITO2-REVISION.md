# Procesamiento de Datos con TypeScript

Ya tienes la web pública de tu empresa funcionando con formularios y validaciones básicas. Ahora tu equipo técnico necesita que construyas las primeras funcionalidades internas que harán que el negocio opere de forma más eficiente.

Tu gerente te ha asignado implementar un conjunto de utilidades de procesamiento de datos que el equipo necesita para el día a día. No se trata de una interfaz completa todavía, eso vendrá después, sino de las funciones base que permitirán gestionar, filtrar, ordenar y transformar la información crítica del negocio. Piensa en esto como la capa lógica que otros sistemas utilizarán más adelante.

Estas utilidades deben estar escritas en **TypeScript**, ser reutilizables, estar correctamente tipadas y poder ejecutarse tanto en el navegador como en entornos de desarrollo. El énfasis está en dominar la manipulación de datos estructurados: colecciones, objetos, búsquedas, ordenamientos y transformaciones.

## 📋 Lo que te piden construir

### Correo recibido

**De:** Tech Lead  
**Para:** Tú  
**Asunto:** Funcionalidades base para procesamiento de datos

Hola,

Necesitamos que implementes un conjunto de funciones TypeScript que nos permitan manejar de forma eficiente los datos principales de la empresa. El objetivo es tener utilidades sólidas y bien tipadas que podamos reutilizar en múltiples contextos.

### Lo que necesitamos

1. **Sistema de gestión de colecciones**  
   Funciones para filtrar, ordenar, buscar y agrupar elementos dentro de arrays. Debes implementar búsqueda lineal para arrays desordenados y búsqueda binaria para arrays ordenados. Asegúrate de manejar correctamente casos vacíos y elementos no encontrados.

2. **Modelado de datos con objetos e interfaces**  
   Define las interfaces TypeScript que representan las entidades principales del negocio. Cada interfaz debe tener tipos explícitos para todas sus propiedades y métodos auxiliares para trabajar con esos datos. Usa objetos literales para representar instancias concretas.

3. **Transformaciones y agregaciones**  
   Implementa funciones que tomen colecciones de objetos y generen reportes simples:
   - Contar elementos por categoría.
   - Sumar valores numéricos.
   - Encontrar máximos y mínimos.
   - Calcular promedios.

   Todo debe estar tipado.

4. **Validaciones de negocio**  
   Crea funciones que validen que los datos cumplan con las reglas específicas de tu empresa antes de ser procesados o almacenados.

   Por ejemplo:
   - Verificar que un elemento tenga todos los campos obligatorios.
   - Verificar que los valores numéricos estén dentro de rangos permitidos.
   - Verificar que las fechas sean coherentes.

El código debe ser limpio, con nombres descriptivos, y cada función debe tener una sola responsabilidad. Queremos que esto sea mantenible a largo plazo.

Revisa el documento de contexto de tu empresa para conocer exactamente qué entidades modelar, qué validaciones aplicar y qué reportes generar.

Saludos,

**Tech Lead**

---

## 💡 Qué debes saber antes de empezar

Este hito se enfoca exclusivamente en lógica de programación y manipulación de datos con TypeScript. Se recomienda que intentes resolver este desafío sin ayuda de IA o, en su defecto, con un uso mínimo de ella, para fortalecer tus habilidades de pensamiento lógico, analítico y de resolución de problemas, fundamentales para cualquier programador.

### Conceptos clave que aplicarás

1. **Arrays y matrices**  
   Cómo almacenar, recorrer, ordenar y buscar elementos en colecciones.

2. **Búsqueda lineal vs búsqueda binaria**  
   Cuándo usar cada una y cómo implementarlas correctamente.

3. **Interfaces y objetos literales**  
   Cómo modelar datos del mundo real en TypeScript con tipos explícitos.

4. **Funciones puras**  
   Escribir funciones que solo trabajen con lo que reciben por parámetros, sin depender de variables globales.

5. **Transformaciones funcionales**  
   Uso de:
   - `.map()`
   - `.filter()`
   - `.reduce()`

   y otros métodos de arrays para transformar datos sin bucles explícitos.

6. **Validaciones**  
   Cómo escribir funciones que verifiquen que los datos cumplen reglas de negocio antes de procesarlos.

---

## 📁 Estructura de archivos esperada

```text
src/
├── types/
│   └── models.ts          # Interfaces y tipos
├── utils/
│   ├── collections.ts     # Funciones para arrays
│   ├── search.ts          # Búsquedas lineal y binaria
│   ├── transformations.ts # Agregaciones y reportes
│   └── validations.ts     # Validaciones de negocio
└── index.html             # Página de prueba (opcional)
# Cómo Iniciar el Proyecto

1. Ve a tu repositorio del proyecto de compañía que ya tienes. Si no lo has creado aún, ve al [repositorio plantilla del proyecto transversal](https://github.com/4GeeksAcademy/ai-engineering-company-project-monorepo) y haz clic en el botón **"Usar esta plantilla"** y selecciona **"Crear un nuevo repositorio"**, o [haz clic aquí](https://github.com/new?template_name=ai-engineering-company-project-monorepo&template_owner=4GeeksAcademy).

2. Una vez tengas tu propio repositorio, ábrelo en **GitHub Codespaces** o clónalo localmente.

3. Lee completamente tu archivo [company-BRIEFING-HITO2-REV.md] antes de escribir código. Allí encontrarás:

   - Las entidades específicas que debes modelar (productos, clientes, pedidos, etc.).
   - Los nombres exactos de los campos y sus tipos.
   - Las reglas de validación específicas de tu empresa.
   - Los reportes que debes generar.

4

5. Organiza tu código en la estructura de carpetas propuesta y comienza a implementar las funciones.

6. Asegúrate de que el proyecto pueda validarse o ejecutarse con un comando claro de TypeScript durante el desarrollo. Por ejemplo:

   ```bash
   npx tsc --noEmit
   ```

7. Comienza a implementar las funciones.

---

# 💻 Lo que Debes Hacer

Implementa las siguientes funcionalidades en TypeScript. Todos los nombres de entidades, campos y reglas deben coincidir exactamente con lo especificado en tu `BRIEFING-HITO2-REV.md`.

## Backend / Lógica
## Backend / Lógica

### ✅ Requisitos Funcionales

- Define las interfaces TypeScript para todas las entidades principales de tu empresa especificadas en tu `BRIEFING-HITO2-REV.md`.
- Implementa funciones de filtrado que permitan buscar elementos por uno o más criterios (por ejemplo: filtrar por categoría, por rango de precio, por estado).
- Implementa funciones de ordenamiento que ordenen arrays según diferentes criterios (ascendente, descendente, por múltiples campos).
- Implementa búsqueda lineal para encontrar elementos en arrays desordenados.
- Implementa búsqueda binaria para encontrar elementos en arrays previamente ordenados.
- Crea funciones de agregación que generen reportes:
  - Contar elementos por categoría.
  - Calcular totales.
  - Calcular promedios.
  - Encontrar valores máximos y mínimos.
- Implementa validaciones de negocio que verifiquen que los objetos cumplen las reglas definidas en tu `BRIEFING-HITO2-REV.md` antes de ser procesados.
- Todas las funciones deben tener tipos explícitos en parámetros y valores de retorno.
- El código debe seguir el principio de responsabilidad única: cada función hace una sola cosa.
- El proyecto incluye un comando claro para validar o ejecutar el código TypeScript durante el desarrollo.

### ⚠️ Importante

Los nombres de campos, tipos de entidades y reglas de validación en tu implementación deben coincidir exactamente con lo especificado en tu `BRIEFING-HITO2-REV.md`.

Una implementación genérica que ignore el contexto no será aceptada.

---

## Frontend / Pruebas (Opcional)

- Crea una página HTML simple con Tailwind CSS que te permita probar tus funciones manualmente.
- Incluye botones o controles para ejecutar diferentes operaciones (filtrar, buscar, ordenar, generar reportes).
- Muestra los resultados de las operaciones en la interfaz de forma clara.

Si agregas una página `index.html` para probar tus funciones manualmente, asegúrate de poder servirla en local o en Codespaces con un comando simple como:

```bash
npx http-server . -p 3000 -a 0.0.0.0
```

---

## Calidad de Código

- Usa nombres descriptivos para variables, funciones e interfaces (camelCase para variables y funciones, PascalCase para interfaces).
- Cada función debe ser pura: trabaja solo con lo que recibe por parámetros, sin modificar variables globales.
- Escribe comentarios solo cuando sea necesario para explicar lógica compleja, no para describir código obvio.
- Maneja correctamente casos vacíos:
  - Arrays vacíos.
  - Elementos no encontrados.
  - Valores nulos.
- Usa `const` por defecto y `let` solo cuando el valor vaya a cambiar.
- Mantén la indentación y el formato consistentes en todo el código.

# ✅ Lo que Evaluaremos

## Corrección técnica

- Las interfaces TypeScript modelan correctamente las entidades especificadas en el `BRIEFING-HITO2-REV.md` con todos sus campos y tipos.
- Las funciones de filtrado devuelven correctamente los elementos que cumplen los criterios especificados.
- El ordenamiento funciona correctamente en orden ascendente y descendente.
- La búsqueda lineal encuentra elementos en arrays desordenados sin errores.
- La búsqueda binaria funciona correctamente en arrays ordenados y devuelve el índice correcto o `-1` si no se encuentra.
- Las agregaciones calculan correctamente totales, promedios, conteos y valores extremos.
- Las validaciones rechazan datos que no cumplen con las reglas de negocio del `BRIEFING-HITO2-REV.md`.
- No hay errores de compilación de TypeScript en ningún archivo.
- Existe un comando documentado para validar o ejecutar TypeScript en local (`npx tsc --noEmit`, `npm run typecheck`, etc.).

---

## Estructura y organización

- El código está organizado en archivos separados por responsabilidad (`types`, `utils`, `validations`).
- Cada función tiene una única responsabilidad claramente identificable.
- Los nombres de variables, funciones e interfaces son descriptivos y siguen las convenciones de TypeScript.

---

## Adaptación al contexto

- Todos los nombres de entidades, campos y tipos coinciden exactamente con los especificados en el `BRIEFING-HITO2-REV.md`.
- Las validaciones implementadas corresponden a las reglas de negocio definidas en el `BRIEFING-HITO2-REV.md`.
- Los reportes generados responden a las necesidades específicas descritas en el `BRIEFING-HITO2-REV.md`.

---

## Calidad de código

- Las funciones son puras: no dependen de variables externas ni modifican estado global.
- Se manejan correctamente casos límite:
  - Arrays vacíos.
  - Elementos no encontrados.
  - Valores nulos.
- El código sigue las mejores prácticas de TypeScript:
  - Tipos explícitos.
  - Uso de `const`/`let` apropiado.
  - Evita `any`.

---

