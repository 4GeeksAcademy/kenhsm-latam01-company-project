## Conocimiento complementario: cómo funciona un flujo de restablecimiento de contraseña

El flujo tiene tres pasos y dos momentos separados en el tiempo:

1. **Solicitud** — El usuario envía su email. El servidor genera un token de restablecimiento (un JWT firmado o una cadena aleatoria almacenada en la base de datos), construye una URL de restablecimiento que contiene ese token (`/reset-password?token=<token>`) y la envía al email del usuario mediante un servicio de correo transaccional.
2. **Restablecimiento** — El usuario hace clic en el enlace, llega a la página `/reset-password`, introduce una nueva contraseña y envía el formulario. El frontend envía el token (leído de la URL) y la nueva contraseña a la API. El servidor valida el token (firma, expiración y que no se haya usado ya), actualiza la contraseña e invalida el token para que no pueda reutilizarse.
3. **Confirmación** — El usuario es redirigido a `/login` y puede iniciar sesión con la nueva contraseña.

### ¿Por qué mostrar siempre un mensaje de confirmación?
Si el formulario muestra "email no encontrado" para direcciones que no existen, un atacante puede usar eso para enumerar qué emails están registrados. Responder siempre con *"si esa dirección está en nuestro sistema, recibirás un enlace"* lo evita.

### Expiración y reutilización
Un token de restablecimiento debe durar **15–60 minutos** y quedar inutilizable tras un reset exitoso. Un JWT con solo un claim `exp` no se puede invalidar después de usarlo. Persiste estado en el servidor: una fila con el token hasheado, un registro de tokens usados, o un `password_changed_at` que rechace tokens emitidos antes de ese momento. Codificar la expiración en el payload del JWT no basta.

Antes de empezar, regístrate en uno de los servicios de email listados arriba y obtén una API key. Guárdala en tu archivo `.env`. Asegúrate de que `.env` está en tu `.gitignore` — nunca hagas commit de API keys.

---

## Qué Debes Hacer

### Backend
* `POST /auth/forgot-password` — Acepta `{ email }`. Si el usuario existe, genera un token de restablecimiento con expiración corta (15–60 minutos) y envía un email con el enlace de restablecimiento. Devuelve siempre `200` independientemente de si el email fue encontrado.
* `POST /auth/reset-password` — Acepta `{ token, new_password }`. Valida el token (firma, expiración y que no se haya usado ya). Si es válido, hashea la nueva contraseña, actualiza el registro del usuario e invalida el token. Devuelve `400` para tokens inválidos, expirados o ya utilizados.
* `POST /auth/change-password` — Acepta `{ current_password, new_password }`. Requiere un token de sesión válido en la cabecera `Authorization`. Verifica la contraseña actual antes de actualizar. Devuelve `400` si la contraseña actual es incorrecta.
* Integra un servicio de correo transaccional para enviar el email de restablecimiento. El email debe incluir el enlace de restablecimiento y ser legible en móvil.
* Almacena la API key del servicio de email en una variable de entorno. Documenta el nombre de la variable en tu `README` o en un `.env.example`.

### Frontend
* `/forgot-password` — Formulario con campo de email. Al enviarlo, llama a `POST /auth/forgot-password` y muestra un mensaje de confirmación (*"Si esa dirección está registrada, recibirás un enlace en breve"*). El formulario debe desactivarse tras el envío para evitar peticiones duplicadas.
* `/reset-password` — Formulario de nueva contraseña con campo de confirmación. Lee el token del query string de la URL. Al enviarlo, llama a `POST /auth/reset-password`. Si tiene éxito, redirige a `/login` con un mensaje de éxito. Si falla (token expirado o inválido), muestra un error claro y un enlace de vuelta a `/forgot-password`.
* `/account/change-password` — Formulario con la contraseña actual, la nueva contraseña y la confirmación. Valida que la nueva contraseña y la confirmación coinciden antes de llamar a la API.
* Añade un enlace *"¿Olvidaste tu contraseña?"* en la página `/login` que apunte a `/forgot-password`.

### Seguridad
* Los tokens de restablecimiento deben expirar e invalidarse tras su uso — un token no puede usarse dos veces.
* El endpoint `/forgot-password` debe devolver siempre `200`, nunca revelar si un email está registrado.
* Las API keys no deben aparecer nunca en el código fuente — usa exclusivamente variables de entorno.

---

## 🚀 Para ir más lejos (opcional)
*No se evalúan, pero son extensiones válidas si el tiempo lo permite:*
* **Plantilla de email en HTML** — Envía un email con estilos en lugar de un enlace en texto plano.
* **Rate limiting** — Limita el número de solicitudes de restablecimiento por dirección de email por hora para prevenir abusos.
* **Registro de auditoría** — Registra cada evento de restablecimiento de contraseña (`timestamp`, dirección IP) en la base de datos.

---

## ✅ Qué Vamos a Evaluar
* `POST /auth/forgot-password` envía un email real con el enlace de restablecimiento cuando se llama con una dirección registrada.
* `POST /auth/forgot-password` devuelve `200` incluso cuando la dirección no está registrada — no se filtra información.
* El token de restablecimiento expira tras la ventana configurada y no puede usarse después de expirar.
* `POST /auth/reset-password` actualiza la contraseña e invalida el token en caso de éxito.
* `POST /auth/reset-password` devuelve `400` para tokens expirados o ya utilizados.
* `/forgot-password` muestra un mensaje de confirmación tras el envío independientemente del resultado.
* `/reset-password` lee el token de la URL, envía el formulario y redirige a `/login` en caso de éxito.
* `/reset-password` muestra un error claro con un enlace de vuelta a `/forgot-password` cuando el token es inválido o ha expirado.
* La página `/login` tiene un enlace visible a *"¿Olvidaste tu contraseña?"*.
* `/account/change-password` valida que la nueva contraseña y la confirmación coinciden, llama a la API y muestra feedback de éxito o error.
* `POST /auth/change-password` rechaza contraseñas actuales incorrectas con `400`.
* Ninguna API key está en el código fuente — todos los secretos se cargan desde variables de entorno.