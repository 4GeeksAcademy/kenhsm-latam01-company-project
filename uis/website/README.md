# Sitio público Brasaland

Landing corporativa en español y formulario de registro simulado de Brasa Points. El formulario no persiste ni transmite datos personales.

## Ejecutar localmente

Desde la raíz del repositorio, ejecuta:

```sh
npx --yes http-server uis/website -p 3000 -a 0.0.0.0
```

Abre `http://localhost:3000`. En Codespaces, reenvía el puerto 3000 y cambia su visibilidad a **Public** para que la vista previa pueda auditarse externamente. La landing está en `/` y el registro en `/application.html`.

Tailwind se carga con su CDN Play para mantener este entregable estático, sin proceso de build. Para registrar Brasa Points en producción se necesita conectar un backend con consentimiento y tratamiento de datos adecuados.
