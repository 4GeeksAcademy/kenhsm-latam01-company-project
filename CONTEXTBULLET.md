## Auditoría y Pruebas de Autenticación

La API de autenticación de tu empresa está en producción, gestionando usuarios y sesiones reales. La semana pasada, un compañero subió un pequeño refactor que rompió la lógica de expiración de tokens — ninguna prueba lo detectó, y los usuarios reportaron estar bloqueados durante dos horas antes de que alguien se diera cuenta. La respuesta del CTO fue breve y directa: *"Necesitamos una batería de pruebas. El código sin tests no es código de producción."*

Tu tarea es añadir una batería completa de pruebas unitarias a la API de autenticación que construiste en el hito anterior. Trabajarás al nivel de la lógica de funciones y endpoints — no probando la serialización HTTP ni las tuberías del framework, sino la lógica de negocio real: 
* ¿Se genera correctamente el token? 
* ¿Se rechaza un token expirado? 
* ¿Qué ocurre cuando el campo de contraseña está vacío?

> No se trata de escribir pruebas por el mero hecho de escribirlas. Se trata de construir la confianza de que cada endpoint se comporta como se espera en condiciones normales, en casos límite y en escenarios de fallo — los tres pilares de cualquier plan de pruebas serio.