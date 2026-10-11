# Carpeta `mcps`

Esta carpeta contiene los **Servidores Model Context Protocol (MCP)** que exponen herramientas, recursos y contexto a los modelos y agentes de IA.

Cada subcarpeta dentro de `mcps/` debe corresponder a **un servidor MCP concreto** (por ejemplo `database-mcp`, `github-mcp`) e incluir su propia documentación.

- **Propósito principal**: centralizar los servidores que actúan como puente entre los modelos de IA y los sistemas internos o fuentes de datos de la compañía.
- **Recomendación**: documenta las herramientas y recursos que expone cada servidor MCP.

## Servidores disponibles

- [`brasaland`](./brasaland/README.md): tools Streamable HTTP con OAuth para incidencias e inventario de solo lectura.
