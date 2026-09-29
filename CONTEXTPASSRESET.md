El sistema de autenticación está funcionando. Los usuarios pueden registrarse, iniciar sesión y gestionar su perfil.

¿Pero qué ocurre cuando olvidan su contraseña — o necesitan cambiarla estando conectados?

Ahora mismo, un usuario que olvida su contraseña no tiene forma de recuperar su cuenta. Los usuarios con sesión iniciada no tienen un formulario para actualizar su contraseña. En cualquier sistema en producción, ambos flujos son requisitos básicos de seguridad. Tu plataforma no tiene ningún mecanismo para ninguno de los dos.

Tu tech lead ha abierto el ticket:

## AUTH-03 — Recuperación y cambio de contraseña

La plataforma necesita dos mecanismos de contraseña — restablecimiento cuando el usuario la olvidó, y cambio estando conectado. Esto cubre tanto la API como el frontend:

### Backend

* `POST /auth/forgot-password` — Recibe un email, valida que el usuario existe, genera un token de restablecimiento firmado de corta duración y envía un enlace de restablecimiento a la dirección del usuario.
* `POST /auth/reset-password` — Recibe el token de restablecimiento y una nueva contraseña, valida el token (firma + expiración), hashea la nueva contraseña y actualiza el registro del usuario. El token debe quedar invalidado tras su uso.
* `POST /auth/change-password` — Endpoint autenticado. Recibe la contraseña actual y una nueva, verifica la actual, hashea la nueva y actualiza el registro del usuario.

### Frontend

* `/forgot-password` — Formulario donde el usuario introduce su email. Siempre muestra un mensaje de confirmación tras el envío, independientemente de si la dirección existe, para evitar la enumeración de usuarios.
* `/reset-password` — Formulario donde el usuario establece una nueva contraseña. Lee el token de restablecimiento del query string de la URL y lo envía a la API junto con la nueva contraseña. Si tiene éxito, redirige a `/login`.
* `/account/change-password` — Formulario con la contraseña actual, la nueva contraseña y la confirmación. Valida que la nueva contraseña y la confirmación coinciden antes de llamar a la API.

---

### Integración de Correo

Para el envío de correos, elige el siguiente servicio e intégralo:
* **Resend**