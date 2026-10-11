from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import InsufficientScopeError, ToolError
from mcpauth import AuthInfo, MCPAuth
from mcpauth.config import AuthServerConfig, AuthServerType, AuthorizationServerMetadata
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from brasaland_shared.incidents import MODEL_BRANCHES, MODEL_CATEGORIES, MODEL_ORIGINS, MODEL_STATUSES
from brasaland_mcp.api_client import BrasalandAPIClient, BrasalandAPIError

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("brasaland_mcp.tools")

GLOBAL_SCOPE = "mcp:access"
TOOL_SCOPES = {
    "incidents:create": "Create incident tickets.",
    "incidents:read": "Read incident tickets.",
    "incidents:status": "Advance incident tickets through allowed lifecycle transitions.",
    "inventory:read": "Read inventory only.",
    "inventory:write": "Reserved scope; inventory writes are disabled by policy.",
}

IncidentCategory = Enum("IncidentCategory", {value: value for value in MODEL_CATEGORIES}, type=str)
IncidentOrigin = Enum("IncidentOrigin", {value: value for value in MODEL_ORIGINS}, type=str)
IncidentBranch = Enum("IncidentBranch", {value: value for value in MODEL_BRANCHES}, type=str)
IncidentStatus = Enum("IncidentStatus", {value: value for value in MODEL_STATUSES}, type=str)


def _auth_settings() -> tuple[str, str, str, str, str]:
    issuer = os.getenv("MCP_AUTH_ISSUER", "http://127.0.0.1:9000").rstrip("/")
    auth_url = os.getenv("MCP_AUTHORIZATION_ENDPOINT", f"{issuer}/authorize")
    token_url = os.getenv("MCP_TOKEN_ENDPOINT", f"{issuer}/token")
    jwks_url = os.getenv("MCP_JWKS_URI", f"{issuer}/.well-known/jwks.json")
    audience = os.getenv("MCP_AUTH_AUDIENCE", os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8787")).rstrip("/")
    return issuer, auth_url, token_url, jwks_url, audience


def _make_auth(verify_token: Any = "jwt") -> MCPAuth:
    issuer, auth_url, token_url, jwks_url, _ = _auth_settings()
    server = AuthServerConfig(
        type=AuthServerType.OIDC,
        metadata=AuthorizationServerMetadata(
            issuer=issuer,
            authorization_endpoint=auth_url,
            token_endpoint=token_url,
            jwks_uri=jwks_url,
            response_types_supported=["code"],
            grant_types_supported=["authorization_code", "refresh_token"],
            code_challenge_methods_supported=["S256"],
            scope_supported=[GLOBAL_SCOPE, *TOOL_SCOPES],
        ),
    )
    return MCPAuth(server=server)


def _client_label(auth: MCPAuth) -> str:
    info = auth.auth_info
    return (info.client_id or info.subject) if info else "unknown"


def _require_scope(auth: MCPAuth, scope: str) -> AuthInfo:
    info = auth.auth_info
    if info is None:
        raise ToolError("AUTHENTICATION_REQUIRED: provide a valid OAuth bearer token.")
    if scope not in info.scopes:
        raise InsufficientScopeError([scope], message=f"INSUFFICIENT_SCOPE: token requires '{scope}'.")
    return info


def _audit(tool: str, client: str, result: str) -> None:
    logger.info("tool_invocation tool=%s client=%s result=%s", tool, client, result)


def _api_failure(error: BrasalandAPIError) -> ToolError:
    return ToolError(f"{error.code}: {error.message}")


def create_server(*, api: BrasalandAPIClient | None = None, auth: MCPAuth | None = None) -> tuple[FastMCP, MCPAuth]:
    api = api or BrasalandAPIClient()
    auth = auth or _make_auth()
    mcp = FastMCP(
        name="Brasaland Company Tools",
        instructions=(
            "Manage Brasaland incident tickets and read current inventory. Ticket status changes "
            "must follow the Incidents Manager lifecycle. Inventory is read-only; write attempts are rejected."
        ),
    )

    @mcp.tool(
        name="create_incident",
        title="Create an incident ticket",
        description=(
            "Create a Brasaland Incidents Manager ticket. Required values: title, description, category, origin, and branch. "
            f"category must be one of {', '.join(MODEL_CATEGORIES)}; origin one of {', '.join(MODEL_ORIGINS)}; "
            f"branch one of {', '.join(MODEL_BRANCHES)}. New tickets start as 'open'. Requires incidents:create."
        ),
    )
    async def create_incident(
        title: str,
        description: str,
        category: IncidentCategory,
        origin: IncidentOrigin,
        branch: IncidentBranch,
    ) -> dict[str, Any]:
        tool, client_name = "create_incident", _client_label(auth)
        try:
            _require_scope(auth, "incidents:create")
            result = await api.create_incident({
                "title": title,
                "description": description,
                "category": category.value,
                "status": "open",
                "origin": origin.value,
                "branch": branch.value,
            })
            _audit(tool, client_name, "success")
            return result
        except BrasalandAPIError as error:
            _audit(tool, client_name, error.code)
            raise _api_failure(error) from error
        except Exception as error:
            _audit(tool, client_name, "error")
            raise

    @mcp.tool(
        name="get_incident",
        title="Get an incident ticket",
        description="Return one incident by its Brasaland incident UUID, including status and timestamps. Requires incidents:read.",
    )
    async def get_incident(incident_id: str) -> dict[str, Any]:
        tool, client_name = "get_incident", _client_label(auth)
        try:
            _require_scope(auth, "incidents:read")
            result = await api.get_incident(incident_id)
            _audit(tool, client_name, "success")
            return result
        except BrasalandAPIError as error:
            _audit(tool, client_name, error.code)
            raise _api_failure(error) from error
        except Exception:
            _audit(tool, client_name, "error")
            raise

    @mcp.tool(
        name="update_incident_status",
        title="Advance incident ticket status",
        description=(
            "Change a ticket's status through the Incidents Manager lifecycle endpoint. Allowed values are "
            "open, in_progress, resolved, discarded; transitions are enforced by the backend. "
            "This tool calls PATCH /api/incidents/{incident_id}/status, never a generic incident PATCH. Requires incidents:status."
        ),
    )
    async def update_incident_status(incident_id: str, status: IncidentStatus) -> dict[str, Any]:
        tool, client_name = "update_incident_status", _client_label(auth)
        try:
            _require_scope(auth, "incidents:status")
            result = await api.update_incident_status(incident_id, status.value)
            _audit(tool, client_name, "success")
            return result
        except BrasalandAPIError as error:
            _audit(tool, client_name, error.code)
            raise _api_failure(error) from error
        except Exception:
            _audit(tool, client_name, "error")
            raise

    @mcp.tool(
        name="list_inventory",
        title="Read Brasaland inventory",
        description=(
            "Read-only query of current Brasaland inventory. Optionally filter by location_id (for example COL-01 or FLA-02) "
            "and/or ingredient (for example carne_res_kg). Results use the operations API fields location_id, ingredient, quantity. "
            "Requires inventory:read. This server cannot modify inventory."
        ),
        annotations={"readOnlyHint": True, "destructiveHint": False},
    )
    async def list_inventory(location_id: str | None = None, ingredient: str | None = None) -> list[dict[str, Any]]:
        tool, client_name = "list_inventory", _client_label(auth)
        try:
            _require_scope(auth, "inventory:read")
            records = await api.list_inventory()
            if location_id:
                records = [item for item in records if item["location_id"] == location_id]
            if ingredient:
                records = [item for item in records if item["ingredient"] == ingredient]
            _audit(tool, client_name, "success")
            return records
        except BrasalandAPIError as error:
            _audit(tool, client_name, error.code)
            raise _api_failure(error) from error
        except Exception:
            _audit(tool, client_name, "error")
            raise

    @mcp.tool(
        name="write_inventory",
        title="Attempt inventory write (disabled)",
        description=(
            "This operation is intentionally disabled. Brasaland inventory is read-only through MCP. "
            "Every invocation is rejected with READ_ONLY, regardless of the requested quantity or OAuth scopes. "
            "Use list_inventory for queries. Requires inventory:write to receive the explicit policy rejection."
        ),
        annotations={"readOnlyHint": False, "destructiveHint": True},
    )
    async def write_inventory(location_id: str, ingredient: str, quantity: float) -> None:
        tool, client_name = "write_inventory", _client_label(auth)
        try:
            _require_scope(auth, "inventory:write")
            _audit(tool, client_name, "READ_ONLY")
            raise ToolError("READ_ONLY: inventory is read-only; MCP rejected this write and made no API request.")
        except Exception:
            if auth.auth_info and "inventory:write" not in auth.auth_info.scopes:
                _audit(tool, client_name, "INSUFFICIENT_SCOPE")
            raise

    return mcp, auth


def create_app(*, verify_token: Any = "jwt", api: BrasalandAPIClient | None = None) -> Starlette:
    mcp, auth = create_server(api=api, auth=_make_auth(verify_token))
    mcp_app = mcp.http_app(path="/mcp", transport="streamable-http", stateless_http=True)
    _, _, _, _, audience = _auth_settings()
    mcp_app.add_middleware(
        auth.bearer_auth_middleware(
            verify_token,
            audience=audience,
            required_scopes=[GLOBAL_SCOPE],
            show_error_details=False,
        )
    )

    class ResourceMetadataChallengeMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Response:
            response = await call_next(request)
            if response.status_code == 401:
                response.headers["WWW-Authenticate"] = (
                    'Bearer resource_metadata="'
                    f'{os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8787").rstrip("/")}'
                    '/.well-known/oauth-protected-resource/mcp"'
                )
            elif response.status_code == 403:
                response.headers["WWW-Authenticate"] = 'Bearer error="insufficient_scope"'
            return response

    mcp_app.add_middleware(ResourceMetadataChallengeMiddleware)

    async def protected_resource_metadata(request: Request) -> JSONResponse:
        issuer, _, _, _, _ = _auth_settings()
        server_url = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8787").rstrip("/")
        return JSONResponse({
            "resource": f"{server_url}/mcp",
            "authorization_servers": [issuer],
            "scopes_supported": [GLOBAL_SCOPE, *TOOL_SCOPES],
            "bearer_methods_supported": ["header"],
        })

    return Starlette(routes=[
        Route("/.well-known/oauth-protected-resource", protected_resource_metadata, methods=["GET"]),
        Route("/.well-known/oauth-protected-resource/mcp", protected_resource_metadata, methods=["GET"]),
        Mount("/", app=mcp_app),
    ])


def run() -> None:
    import uvicorn

    app = create_app()
    uvicorn.run(app, host=os.getenv("MCP_HOST", "0.0.0.0"), port=int(os.getenv("MCP_PORT", "8787")))


if __name__ == "__main__":
    run()
