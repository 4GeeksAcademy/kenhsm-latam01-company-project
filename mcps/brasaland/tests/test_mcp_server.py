from __future__ import annotations

import logging

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from mcpauth import AuthInfo
from starlette.testclient import TestClient

from brasaland_mcp.api_client import BrasalandAPIClient
from brasaland_mcp.server import create_app, create_server


class FakeAPI:
    def __init__(self):
        self.calls = []

    async def create_incident(self, payload):
        self.calls.append(("create", payload))
        return {"id": "incident-1", **payload}

    async def get_incident(self, incident_id):
        self.calls.append(("get", incident_id))
        return {"id": incident_id, "status": "open"}

    async def update_incident_status(self, incident_id, status):
        self.calls.append(("status", incident_id, status))
        return {"id": incident_id, "status": status}

    async def list_inventory(self):
        self.calls.append(("inventory",))
        return [{"location_id": "COL-01", "ingredient": "carne_res_kg", "quantity": 42.5}]


def auth_info(scopes: list[str], token: str = "token") -> AuthInfo:
    return AuthInfo(
        token=token,
        issuer="https://issuer.example.test",
        client_id="playground-client",
        scopes=scopes,
        subject="service-user-17",
        audience="https://brasaland-mcp.example.test",
        claims={"sub": "service-user-17"},
    )


@pytest.mark.parametrize(
    ("authorization", "expected_status"),
    [(None, 401), ("Bearer no-global-scope", 403)],
)
def test_mcp_endpoint_requires_oauth_and_global_scope(monkeypatch, authorization, expected_status):
    monkeypatch.setenv("MCP_AUTH_ISSUER", "https://issuer.example.test")
    monkeypatch.setenv("MCP_AUTH_AUDIENCE", "https://brasaland-mcp.example.test")

    def verify(token):
        return auth_info(["incidents:read"], token)

    client = TestClient(create_app(verify_token=verify), raise_server_exceptions=False)
    headers = {"Authorization": authorization} if authorization else {}
    response = client.post("/mcp", headers=headers)

    assert response.status_code == expected_status
    assert response.headers["www-authenticate"].startswith("Bearer")
    if expected_status == 401:
        assert "oauth-protected-resource/mcp" in response.headers["www-authenticate"]
    else:
        assert 'error="insufficient_scope"' in response.headers["www-authenticate"]


def test_protected_resource_metadata_is_public_and_discoverable(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_URL", "https://mcp.example.test")
    monkeypatch.setenv("MCP_AUTH_ISSUER", "https://issuer.example.test")
    client = TestClient(create_app())

    response = client.get("/.well-known/oauth-protected-resource")
    path_specific = client.get("/.well-known/oauth-protected-resource/mcp")

    assert response.status_code == 200
    assert path_specific.status_code == 200
    assert response.json()["resource"] == "https://mcp.example.test/mcp"
    assert response.json()["authorization_servers"] == ["https://issuer.example.test"]
    assert "inventory:read" in response.json()["scopes_supported"]


@pytest.mark.asyncio
async def test_discovery_incident_lifecycle_and_tool_audit(caplog):
    api = FakeAPI()
    mcp, auth = create_server(api=api)
    auth._context_var.set(auth_info(["mcp:access", "incidents:create", "incidents:status", "incidents:read"]))

    with caplog.at_level(logging.INFO, logger="brasaland_mcp.tools"):
        async with Client(mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert {"create_incident", "get_incident", "update_incident_status", "list_inventory", "write_inventory"} <= tools.keys()
            assert "PATCH /api/incidents/{incident_id}/status" in tools["update_incident_status"].description
            assert "read-only" in tools["list_inventory"].description.lower()

            created = await client.call_tool(
                "create_incident",
                {
                    "title": "Equipo fuera de servicio",
                    "description": "El refrigerador no mantiene temperatura.",
                    "category": "equipment_failure",
                    "origin": "branch",
                    "branch": "medellin_centro",
                },
            )
            assert created.data["status"] == "open"

            fetched = await client.call_tool("get_incident", {"incident_id": "incident-1"})
            assert fetched.data == {"id": "incident-1", "status": "open"}

            result = await client.call_tool(
                "update_incident_status",
                {"incident_id": "incident-42", "status": "in_progress"},
            )

    assert result.data == {"id": "incident-42", "status": "in_progress"}
    assert api.calls == [
        ("create", {
            "title": "Equipo fuera de servicio",
            "description": "El refrigerador no mantiene temperatura.",
            "category": "equipment_failure",
            "status": "open",
            "origin": "branch",
            "branch": "medellin_centro",
        }),
        ("get", "incident-1"),
        ("status", "incident-42", "in_progress"),
    ]
    assert "tool_invocation tool=update_incident_status client=playground-client result=success" in caplog.text


@pytest.mark.asyncio
async def test_inventory_query_requires_scope_and_write_is_explicitly_denied():
    api = FakeAPI()
    mcp, auth = create_server(api=api)
    auth._context_var.set(auth_info(["mcp:access", "inventory:read"]))

    async with Client(mcp) as client:
        inventory = await client.call_tool("list_inventory", {"location_id": "COL-01"})
        assert inventory.data == [{"location_id": "COL-01", "ingredient": "carne_res_kg", "quantity": 42.5}]
        with pytest.raises(ToolError, match="INSUFFICIENT_SCOPE"):
            await client.call_tool("write_inventory", {"location_id": "COL-01", "ingredient": "carne_res_kg", "quantity": 1})

    assert api.calls == [("inventory",)]

    auth._context_var.set(auth_info(["mcp:access", "inventory:write"]))
    async with Client(mcp) as client:
        with pytest.raises(ToolError, match="READ_ONLY"):
            await client.call_tool("write_inventory", {"location_id": "COL-01", "ingredient": "carne_res_kg", "quantity": 1})

    assert api.calls == [("inventory",)]


@pytest.mark.asyncio
async def test_status_client_uses_lifecycle_endpoint_and_api_bearer():
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"id": "incident-7", "status": "resolved"})

    transport_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = BrasalandAPIClient(
        base_url="https://api.example.test",
        token="server-secret",
        client=transport_client,
    )

    result = await api.update_incident_status("incident-7", "resolved")
    await transport_client.aclose()

    assert result["status"] == "resolved"
    assert requests[0].method == "PATCH"
    assert requests[0].url.path == "/api/incidents/incident-7/status"
    assert requests[0].headers["authorization"] == "Bearer server-secret"
    assert requests[0].read() == b'{"status":"resolved"}'
