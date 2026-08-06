## 📋 Lo que necesitamos

*   **Sistema de gestión de colecciones:** Funciones para filtrar, ordenar, buscar y agrupar elementos dentro de arrays. Debes implementar búsqueda lineal para arrays desordenados y búsqueda binaria para arrays ordenados. Asegúrate de manejar correctamente casos vacíos y elementos no encontrados.
*   **Modelado de datos con objetos e interfaces:** Define las interfaces TypeScript que representan las entidades principales del negocio. Cada interfaz debe tener tipos explícitos para todas sus propiedades y métodos auxiliares para trabajar con esos datos. Usa objetos literales para representar instancias concretas.
*   **Transformaciones y agregaciones:** Implementa funciones que tomen colecciones de objetos y generen reportes simples: contar elementos por categoría, sumar valores numéricos, encontrar máximos y mínimos, calcular promedios. Todo debe estar tipado.
*   **Validaciones de negocio:** Crea funciones que validen que los datos cumplan con las reglas específicas de tu empresa antes de ser procesados o almacenados. Por ejemplo, verificar que un elemento tenga todos los campos obligatorios, que los valores numéricos estén dentro de rangos permitidos, o que las fechas sean coherentes.

> **Nota:** El código debe ser limpio, con nombres descriptivos, y cada función debe tener una sola responsabilidad. Queremos que esto sea mantenible a largo plazo.

---

## 💡 Conceptos clave que aplicarás

*   **Arrays y matrices:** Cómo almacenar, recorrer, ordenar y buscar elementos en colecciones.
*   **Búsqueda lineal vs búsqueda binaria:** Cuándo usar cada una y cómo implementarlas correctamente.
*   **Interfaces y objetos literales:** Cómo modelar datos del mundo real en TypeScript con tipos explícitos.
*   **Funciones puras:** Escribir funciones que solo trabajen con lo que reciben por parámetros, sin depender de variables globales.
*   **Transformaciones funcionales:** Uso de `.map()`, `.filter()`, `.reduce()` y otros métodos de arrays para transformar datos sin bucles explícitos.
*   **Validaciones:** Cómo escribir funciones que verifiquen que los datos cumplen reglas de negocio antes de procesarlos.

---

## 📁 Estructura de archivos esperada

Tu implementación debe organizarse en archivos TypeScript separados por responsabilidad:

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

### Calidad de Código
* Usa **nombres descriptivos** para variables, funciones e interfaces (camelCase para variables y funciones, PascalCase para interfaces)
* Cada función debe ser **pura**: trabaja solo con lo que recibe por parámetros, sin modificar variables globales
* Escribe **comentarios** solo cuando sea necesario para explicar lógica compleja, no para describir código obvio
* Maneja correctamente **casos vacíos**: arrays vacíos, elementos no encontrados, valores nulos
* Usa **const** por defecto y **let** solo cuando el valor vaya a cambiar
* Mantén la **indentación** y el formato consistentes en todo el código

---

### ✅ Poner atención en

**Corrección técnica**
* Las interfaces TypeScript modelan correctamente las entidades especificadas en el CONTEXT.md con todos sus campos y tipos
* Las funciones de filtrado devuelven correctamente los elementos que cumplen los criterios especificados
* El ordenamiento funciona correctamente en orden ascendente y descendente
* La búsqueda lineal encuentra elementos en arrays desordenados sin errores
* La búsqueda binaria funciona correctamente en arrays ordenados y devuelve el índice correcto o -1 si no se encuentra
* Las agregaciones calculan correctamente totales, promedios, conteos y valores extremos
* Las validaciones rechazan datos que no cumplen con las reglas de negocio del CONTEXT.md
* No hay errores de compilación de TypeScript en ningún archivo
* Existe un comando documentado para validar o ejecutar TypeScript en local (`npx tsc --noEmit`, `npm run typecheck`, etc.)

**Estructura y organización**
* El código está organizado en archivos separados por responsabilidad (types, utils, validations)
* Cada función tiene una única responsabilidad claramente identificable
* Los nombres de variables, funciones e interfaces son descriptivos y siguen las convenciones de TypeScript

**Adaptación al contexto**
* Todos los nombres de entidades, campos y tipos coinciden exactamente con los especificados en el CONTEXTHITO2.md
* Las validaciones implementadas corresponden a las reglas de negocio definidas en el CONTEXTHITO2.md
* Los reportes generados responden a las necesidades específicas descritas en el CONTEXTHITO2.md

**Calidad de código**
* Las funciones son puras: no dependen de variables externas ni modifican estado global
* Se manejan correctamente casos límite: arrays vacíos, elementos no encontrados, valores nulos
* El código sigue las mejores prácticas de TypeScript: tipos explícitos, uso de const/let apropiado, evita any