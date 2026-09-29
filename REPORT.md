# Informe de mejoras de rendimiento

Fecha: 2026-09-27

## Cambios aplicados

- Se añadieron metadatos `description` y `theme-color` a `uis/website/index.html` y `uis/backoffice/index.html`.
- Se elimino la peticion 404 de favicon mediante un favicon embebido.
- Se extrajo `uis/shared/dom.js` y ambos frontends usan `mountApp` para montar su contenido inicial.
- No se añadieron imagenes, fuentes externas ni librerias: las vistas no cargan esos recursos y añadirlos empeoraria el peso inicial.

## Comparativa

| Frontend | Modo | Performance antes | Performance despues | Otras categorias | Resultado |
| --- | --- | ---: | ---: | --- | --- |
| Website | Desktop | N/D | N/D | N/D | Lighthouse bloqueado por dependencia del sistema |
| Website | Mobile | N/D | N/D | N/D | Lighthouse bloqueado por dependencia del sistema |
| Backoffice | Desktop | N/D | N/D | N/D | Lighthouse bloqueado por dependencia del sistema |
| Backoffice | Mobile | N/D | N/D | N/D | Lighthouse bloqueado por dependencia del sistema |

No es valido afirmar una mejora numerica sin una ejecucion real. Lighthouse 13.5.0 no pudo arrancar Chromium porque falta `libatk-1.0.so.0`; el usuario del contenedor no puede instalarla. La comparacion numerica debe repetirse en Chrome/Chromium con sus dependencias GTK disponibles, manteniendo las mismas URLs y modos.

## Impacto esperado y evidencia

- **SEO:** impacto directo esperado por la descripcion util para buscadores y la configuracion de tema. Se comprobo que ambos HTML sirven los metadatos.
- **Carga inicial:** se elimina una peticion fallida de favicon, reduciendo ruido y una solicitud de red innecesaria.
- **Mantenibilidad:** ambos entrypoints comparten el montaje DOM; el cambio no altera el HTML renderizado ni el flujo de analisis de incidencias.
- **Core Web Vitals:** no se encontraron imagenes, fuentes externas, bloqueos de render ni trabajo pesado en el arranque. No se afirma mejora de LCP, CLS o INP sin medicion de navegador.

## Verificacion ejecutada

```text
node --check uis/shared/dom.js
node --check uis/website/main.js
node --check uis/backoffice/main.js
curl -fsS http://127.0.0.1:4173/
curl -fsS http://127.0.0.1:4174/
curl -fsSI http://127.0.0.1:4173/
curl -fsSI http://127.0.0.1:4174/
```

Todos los checks anteriores terminaron correctamente; las respuestas HTTP fueron `200`.
