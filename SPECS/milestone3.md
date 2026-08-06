## Mi idea de Agente de IA

###¿Qué información necesitaría (Entradas)?
Para que el agente tome buenas decisiones y no tenga que "adivinar", necesitaría:

-Ventas del día: Cuántos platos exactos se vendieron hoy en ese local(de los 14 que hay).

-Las recetas: Cuántos gramos de carne, pan y salsas lleva cada plato vendido, por poner un ejemplo.

-El inventario actual: Lo que se supone que queda en las neveras según lo que entró, menos lo que se vendió.

-Historial y calendario: Qué día de la semana es mañana, si es festivo, o hay alguna situación que pueda afectar las ventas.

###¿Qué produciría o desencadenaría (Salidas)?

-El agente no solo pensaria, sino que tomaría decisiones que ahorrarían tiempo al equipo:

-Generación de pedidos: Arma automáticamente el "carrito de compras" con las cantidades exactas que faltan y se lo envía al gerente del local, para su aprobación.

-Alertas de emergencia: Envía un mensaje instantáneo si detecta que un ingrediente vital se está agotando rápido en un local específico.

-Datos consolidados para la central: Manda un reporte automático a Lucía (en Medellín) sumando todo lo que van a pedir los 14 locales juntos, dándole poder para exigirle mejores precios a los proveedores.
# Contexto del proyecto

El departamento de People & Talent de tu empresa esta en medio de una campana de seleccion activa. La posicion abierta ha recibido mas de 100 candidaturas en menos de dos semanas y el equipo esta desbordado: llevan el seguimiento de los candidatos en una hoja de calculo compartida, escriben las notas de las entrevistas en documentos separados y actualizan los estados manualmente por hilos de correo. El proceso se esta desmoronando.

El equipo de Tecnologia ya ha construido y expuesto una API REST para gestionar el pipeline de candidaturas. Tu trabajo es construir el frontend que el equipo de People empezara a usar el lunes. El sistema debe permitir ver todas las candidaturas de un vistazo, filtrarlas por estado y por etapa, y acceder al detalle de cada una sin perder el contexto del listado.

La responsable de People ha compartido lo que necesitan con urgencia:

## Lo que la herramienta debe hacer

- Mostrar todas las candidaturas en un listado: nombre, puesto, estado actual y etapa actual de un vistazo.
- Permitir filtrar por estado y por etapa, y buscar por nombre o email sin recargar la pagina.
- Abrir la vista de detalle de un candidato y, desde ahi, cambiar su estado o etapa con una sola interaccion.
- Anadir notas internas a una candidatura y eliminarlas cuando ya no sean relevantes.
- Registrar nuevas candidaturas directamente desde la interfaz y editar los datos de una cuando haya que corregir algo.
