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
