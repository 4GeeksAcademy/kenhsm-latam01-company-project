4. Crea la estructura básica de tu proyecto:

   ```markdown
   /
   ├── index.html (landing page)
   ├── application.html (formulario de aplicación/registro)
   ├── styles.css (solo si Tailwind CDN no es suficiente)
   └── validation.js (lógica de validación del formulario)
   ```

5. Asegúrate de poder levantar el proyecto en el navegador durante el desarrollo usando un comando compatible con Codespaces desde la raíz del repositorio. Por ejemplo: `npx http-server . -p 3000 -a 0.0.0.0`

6. Comienza por la estructura HTML de la landing page, luego añade estilos con Tailwind, después trabaja en el formulario y finalmente implementa la validación.

---

## 💻 Lo que Necesitas Hacer

### Landing Page

- [ ] Crear `index.html` con estructura HTML5 semántica
- [ ] El proyecto puede ejecutarse localmente con un comando `npx` compatible con Codespaces
- [ ] Implementar un `<header>` con logo/nombre de la empresa y navegación
- [ ] Crear una sección hero que presente la empresa y su propuesta de valor
- [ ] Añadir al menos dos secciones adicionales (características, beneficios, cómo funciona, experiencia, etc.)
- [ ] Implementar un `<footer>` con información de contacto
- [ ] Incluir un enlace/botón que dirija al formulario de aplicación
- [ ] Aplicar estilos con Tailwind CSS usando clases utilitarias
- [ ] Hacer el diseño responsive con breakpoints para móvil, tablet y escritorio
- [ ] Implementar diseño mobile-first
- [ ] Añadir etiquetas `alt` descriptivas a todas las imágenes
- [ ] Usar etiquetas HTML semánticas (`<section>`, `<article>`, `<nav>`, etc.)
- [ ] Implementar atributos ARIA donde sea apropiado (`aria-label`, `role`)
- [ ] Añadir marcado Schema.org para la información de la empresa (tipo Organization o LocalBusiness)
- [ ] Exponer el sitio en una **URL pública de Codespaces** (port forwarding → Public) para que se pueda auditar desde fuera

### Formulario de Aplicación/Registro

- [ ] Crear `application.html` con un formulario estructurado
- [ ] Incluir los campos especificados en tu `BRIEFING-HITO1.md`
- [ ] Usar tipos de input apropiados (`email`, `tel`, `date`, `number`, etc.)
- [ ] Añadir `<label>` asociado correctamente con cada input (usando atributo `for`)
- [ ] Agrupar campos relacionados usando `<fieldset>` y `<legend>` donde sea apropiado
- [ ] Marcar campos obligatorios con el atributo `required`
- [ ] Implementar diseño responsive del formulario
- [ ] Aplicar estilos de Tailwind para el formulario (espaciado, tamaños, estados de foco)
- [ ] Añadir botón de envío y botón secundario para limpiar el formulario
- [ ] Crear `validation.js` para validar todos los campos del formulario
- [ ] Implementar validación en tiempo real (mientras el usuario escribe o al perder foco)
- [ ] Mostrar mensajes de error específicos para cada tipo de validación
- [ ] Estilizar mensajes de error de forma clara y visible
- [ ] Prevenir el envío del formulario si hay errores de validación
- [ ] Mostrar un mensaje de éxito cuando la validación sea correcta (simular envío)

⚠️ **IMPORTANTE:** Los nombres de campos, IDs de entidad y valores específicos del dominio en tu implementación deben coincidir con lo especificado en tu BRIEFING-HITO1.md. Una implementación genérica que ignore el contexto no será aceptada.

---

## ✅ Lo que Evaluaremos

### Estructura y Semántica HTML

- [ ] El HTML usa etiquetas semánticas apropiadas en lugar de `<div>` genéricos
- [ ] Todas las imágenes tienen atributos `alt` descriptivos
- [ ] Los formularios usan `<label>` correctamente asociados con inputs
- [ ] El marcado Schema.org está presente y correctamente implementado
- [ ] La estructura del documento es lógica y jerárquica

### Diseño Responsive y Tailwind

- [ ] El sitio es completamente responsive (se adapta a móvil, tablet y escritorio)
- [ ] Existe un comando documentado y funcional, compatible con Codespaces, para ejecutar el proyecto localmente con `npx`
- [ ] Se usa diseño mobile-first
- [ ] Todos los estilos usan clases utilitarias de Tailwind
- [ ] Los breakpoints de Tailwind (`sm:`, `md:`, `lg:`) se usan apropiadamente
- [ ] No hay CSS personalizado innecesario (solo Tailwind)
- [ ] El diseño es visualmente coherente y profesional
- [ ] El rendimiento se verifica con una puntuación mínima de **80** (ideal: **por encima de 90**) usando [PageSpeed Insights](https://pagespeed.web.dev/) en tu **URL pública de Codespaces** (expón el puerto como **Public**). Si PageSpeed no puede alcanzar Codespaces, ejecuta **Lighthouse** desde las DevTools de Chrome (panel Lighthouse, o la extensión Lighthouse) contra la misma vista previa local/Codespaces e incluye esa captura.

### Accesibilidad

- [ ] Todos los elementos interactivos son accesibles por teclado
- [ ] Los atributos ARIA se usan donde mejoran la accesibilidad
- [ ] El contraste de colores cumple con estándares mínimos
- [ ] La navegación es lógica y predecible
- [ ] Los mensajes de error son anunciados apropiadamente

### Formulario y Validación

- [ ] Todos los campos especificados en el BRIEFING.md están presentes
- [ ] Los tipos de input son apropiados para cada campo
- [ ] La validación con JavaScript funciona correctamente para todos los campos
- [ ] Los mensajes de error son específicos y útiles (no solo "campo inválido")
- [ ] La validación previene el envío de datos incorrectos
- [ ] Los estados visuales del formulario son claros (foco, error, éxito)
- [ ] El botón de limpiar formulario funciona correctamente

### Adherencia al Contexto

- [ ] La landing page refleja fielmente el tipo de empresa y sector especificado en BRIEFING.md
- [ ] El contenido presenta la experiencia y ventajas competitivas de la empresa
- [ ] Los campos del formulario coinciden exactamente con los requeridos en BRIEFING.md
- [ ] Cualquier regla de validación específica del dominio está implementada
- [ ] El tono y contenido son coherentes con una empresa establecida que se digitaliza

---