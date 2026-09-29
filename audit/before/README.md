# Evidencia de medicion inicial

La medicion inicial se intento el 2026-09-27 antes de editar los frontends.

Lighthouse 13.5.0 no pudo generar informes ni capturas porque el Chromium disponible no inicia en este contenedor: falta `libatk-1.0.so.0` y el usuario no tiene permisos para instalar dependencias del sistema. Se conserva esta nota para evitar presentar artefactos o puntuaciones no producidos por Lighthouse.

Escenarios pendientes de ejecutar en un entorno con Chrome funcional:

- Website, desktop: `http://127.0.0.1:4173/`
- Website, mobile: `http://127.0.0.1:4173/`
- Backoffice, desktop: `http://127.0.0.1:4174/`
- Backoffice, mobile: `http://127.0.0.1:4174/`
