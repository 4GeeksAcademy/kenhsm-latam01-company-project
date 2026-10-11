# Brasaland MCP Server

A Streamable HTTP MCP server for the existing Brasaland Incidents Manager and operations inventory API. It uses `mcpauth` as an OAuth/OIDC resource server; FastMCP's built-in authorization helpers are not used.

## Start

```bash
cd mcps/brasaland
cp .env.example .env
uv sync
uv run brasaland-mcp
```

The MCP endpoint is `http://localhost:8787/mcp`. The unauthenticated Protected Resource Metadata endpoint is `http://localhost:8787/.well-known/oauth-protected-resource`. Configure these environment values for the deployed OAuth 2.1/OIDC provider and backend:

| Variable | Purpose |
| --- | --- |
| `MCP_SERVER_URL` | Public base URL advertised in resource metadata. |
| `MCP_AUTH_ISSUER` | Exact issuer claim expected in access tokens. |
| `MCP_AUTHORIZATION_ENDPOINT` | Provider's authorization endpoint. |
| `MCP_TOKEN_ENDPOINT` | Provider's token endpoint. |
| `MCP_JWKS_URI` | Provider's public signing keys, used by `mcpauth` JWT verification. |
| `MCP_AUTH_AUDIENCE` | Audience required in access tokens; defaults to `MCP_SERVER_URL`. |
| `BRASALAND_API_BASE_URL` | Existing FastAPI service URL (default `http://127.0.0.1:8010`). |
| `BRASALAND_API_TOKEN` | Server-side service-account JWT for the existing API; never return or log it. |

Tokens need `mcp:access` for MCP protocol access and a per-tool scope below. API credentials are separate from client OAuth tokens and must be held in the MCP server's secret store.

## Tool discovery and least privilege

| Tool | Scope | Capability |
| --- | --- | --- |
| `create_incident` | `incidents:create` | Creates tickets using the API's `title`, `description`, `category`, `status`, `origin`, and `branch` fields. Status is initialized to `open`; category/origin/branch values match `brasaland_shared.incidents`. |
| `get_incident` | `incidents:read` | Reads one incident by UUID. |
| `update_incident_status` | `incidents:status` | Updates only the lifecycle status via `PATCH /api/incidents/{incident_id}/status`; the backend enforces valid transitions (`open` -> `in_progress`/`discarded`, `in_progress` -> `resolved`/`discarded`). |
| `list_inventory` | `inventory:read` | Reads and optionally filters API fields `location_id`, `ingredient`, and `quantity`. |
| `write_inventory` | `inventory:write` | Deliberate policy-denial tool. Returns `READ_ONLY` and makes no backend request, even when the scope is present. |

The `inventory:write` scope grants no write capability; it only allows a caller to receive the explicit denial. Do not assign this scope to clients unless they need to test the policy response. No MCP tool can mutate inventory.

## Errors and audit

- Missing/invalid/expired bearer tokens: HTTP `401` from `mcpauth` (`MISSING_BEARER_TOKEN` or token verification error).
- Missing `mcp:access` or a tool-specific scope: HTTP `403` at the protocol boundary or an MCP tool error with `INSUFFICIENT_SCOPE`.
- Invalid tool inputs: MCP schema validation error; invalid domain values and illegal lifecycle transitions are rejected by the real API as `VALIDATION_ERROR` (HTTP 400).
- Missing API credential: `API_CREDENTIALS_MISSING` (HTTP 503); API-side invalid/forbidden credentials: `API_UNAUTHENTICATED` (401) / `API_FORBIDDEN` (403); missing incident: `NOT_FOUND` (404).
- Inventory mutation attempt with `inventory:write`: MCP tool error `READ_ONLY`; no API request is made.

Each tool call emits a structured log with the tool name, OAuth client/subject, and success or error code. Tokens and incident contents are not written to the audit log.

## MCP Playground

Run the server on port 8787, forward the port as **Public** in Codespaces, and use the public forwarded URL with `/mcp` in MCP Playground. Configure an OAuth client/access token from the issuer above; `localhost` cannot be reached by the hosted Playground. Exercise create -> get -> status update for incidents, query inventory, then invoke `write_inventory` with `inventory:write` and verify `READ_ONLY`.
