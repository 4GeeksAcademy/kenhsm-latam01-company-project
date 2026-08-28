# Technical Context

## Stack actual del monorepo

1. Monorepo Markdown-first con estructura por dominios (`uis/`, `services/`, `skills/`, `agents/`, etc.).
2. Aplicacion existente en `apps/talent-pipeline-tracker/` basada en Next.js + TypeScript.
3. Nuevos entrypoints iniciales de UI creados en `uis/website` y `uis/backoffice` (HTML/CSS estatico como baseline visible).

## Decisiones de arquitectura tomadas

1. Mantener separacion estricta entre configuracion de agentes de desarrollo (`.agents/`) y codigo de producto (`agents/`, `skills/`).
2. Definir protocolo global en `AGENTS.md` para flujo de entrega obligatorio antes de commit.
3. Centralizar contexto operativo para agentes en `memory-bank/` como fuente activa y actualizable.
4. Estandarizar ubicacion de nuevas interfaces: `uis/website` (publico) y `uis/backoffice` (interno).
5. Reservar `services/` para cualquier API o worker backend futuro.

## Restricciones tecnicas

1. El contexto de empresa es multipais y multimoneda; futuras soluciones deben soportar COP y USD.
2. No introducir cambios destructivos sin confirmacion explicita.
3. Cualquier nueva regla/skill de agente debe incluir criterios verificables.
4. Mantener cambios pequenos, trazables y documentados en README/memory-bank cuando cambie estructura o decisiones.
