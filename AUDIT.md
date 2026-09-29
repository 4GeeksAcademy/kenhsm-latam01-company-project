# Auditoria de rendimiento frontend

Fecha: 2026-09-27
Alcance: `uis/website` (home publica) y `uis/backoffice` (dashboard operativo).

## Medicion inicial

La medicion se intento antes de editar el codigo con Lighthouse CLI 13.5.0. Los servidores locales fueron:

- Website: `http://127.0.0.1:4173/`
- Backoffice: `http://127.0.0.1:4174/`

| Frontend | Modo | Performance | Accessibility | Best Practices | SEO | Estado |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Website | Desktop | N/D | N/D | N/D | N/D | Chromium no pudo iniciar |
| Website | Mobile | N/D | N/D | N/D | N/D | Chromium no pudo iniciar |
| Backoffice | Desktop | N/D | N/D | N/D | N/D | Chromium no pudo iniciar |
| Backoffice | Mobile | N/D | N/D | N/D | N/D | Chromium no pudo iniciar |

El intento fue reproducible con Lighthouse y el Chromium descargado por Playwright. El contenedor no incluye `libatk-1.0.so.0` y el usuario `codespace` no tiene permisos para instalar paquetes del sistema, por lo que Chrome termina antes de abrir el puerto de depuracion. No se inventan puntuaciones ni capturas. Para completar la parte visual pendiente, ejecutar el mismo comando en un entorno con Chrome y las librerias GTK instaladas.

Comandos usados:

```sh
CHROME_PATH=/home/codespace/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome \
  npx --yes lighthouse http://127.0.0.1:4173/ --output=html --output=json
```

## Hallazgos y causa raiz

1. **Metadatos SEO ausentes en ambas entradas HTML.** `index.html` solo declaraba charset, viewport y title. Esto dejaba a Lighthouse sin una descripcion util para resultados de busqueda y sin color de tema. Se añadieron `description` y `theme-color` especificos por frontend.
2. **Peticion innecesaria de favicon.** El servidor devolvia `404` para `/favicon.ico` durante la carga inicial. Se declaro un favicon vacio embebido para eliminar esa peticion fallida sin añadir un asset adicional.
3. **Montaje inicial duplicado.** `website/main.js` y `backoffice/main.js` repetian la misma consulta de `#app`, comprobacion nula y asignacion de `innerHTML`. Se extrajo `uis/shared/dom.js` con `mountApp(selector, render)` y se integro en ambos entrypoints. Esto reduce divergencia y deja un punto comun para instrumentacion futura.
4. **Carga inicial pequena y sin imagenes.** La inspeccion del codigo no encontro imagenes, fuentes externas, bundles ni calculos costosos en la carga inicial. Por eso no se aplico una optimizacion de imagen o lazy-loading artificial: no habia recurso que optimizar y añadirlo habria aumentado peso.
5. **Riesgo de INP en backoffice acotado.** El analisis CSV ocurre solo tras submit y la peticion usa `fetch`; no bloquea el arranque. La ruta no se reestructuro porque el comportamiento es apropiado para la vista actual.

## Casos candidatos a refactorizacion

- El montaje del root estaba duplicado en `uis/website/main.js` y `uis/backoffice/main.js`; ahora usa `uis/shared/dom.js`.
- La construccion repetida de paneles/listas del backoffice (`renderRows`, resumen y columnas de analisis) es candidata a extraer un componente de tabla/lista accesible cuando se agreguen nuevas vistas operativas. No se amplio ese refactor en esta auditoria porque solo existe una pantalla consumidora y hacerlo ahora aumentaria el riesgo sin impacto medible de carga.

## Skills

No se instalaron skills externas (`core-web-vitals`, `performance` o `web-perf`): las dos interfaces son HTML/CSS/JS estaticos, el diagnostico de Lighthouse quedo bloqueado por dependencias del contenedor y las correcciones aplicadas son cambios directos y verificables sobre metadatos y codigo compartido.

## Validacion disponible

- `node --check uis/shared/dom.js`
- `node --check uis/website/main.js`
- `node --check uis/backoffice/main.js`
- Ambos servidores locales responden `HTTP 200`.
- Los dos documentos HTML sirven `description`, `theme-color` y favicon embebido.
