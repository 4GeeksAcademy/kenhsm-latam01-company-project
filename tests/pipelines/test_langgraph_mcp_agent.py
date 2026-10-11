from __future__ import annotations

import sys
from pathlib import Path

from data.pipelines import rag as rag_module

SERVICE_SRC = Path(__file__).resolve().parents[2] / "services" / "brasaland-api" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from brasaland_api.modules.agent import graph as agent_graph


def test_agent_dispatches_incident_action_only_through_discovered_mcp_tool(monkeypatch):
    clients = []

    class FakeTool:
        name = "update_incident_status"

        async def ainvoke(self, arguments):
            assert arguments == {"incident_id": "incident-12", "status": "resolved"}
            return {"id": "incident-12", "status": "resolved"}

    class FakeMCPClient:
        def __init__(self, connections, **options):
            clients.append(connections)
            assert options == {"handle_tool_errors": False}

        async def get_tools(self, *, server_name=None):
            assert server_name == "brasaland"
            return [FakeTool()]

    monkeypatch.setattr(agent_graph, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setenv("BRASALAND_MCP_URL", "https://mcp.example.test/mcp")
    monkeypatch.setenv("BRASALAND_MCP_ACCESS_TOKEN", "oauth-access-token")
    monkeypatch.setattr(rag_module, "retrieve", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("RAG should not run for tool action")))

    result = agent_graph.query_agent(
        "Actualiza la incidencia incident-12 a resuelta",
        tool_action="update_incident_status",
        tool_arguments={"incident_id": "incident-12", "status": "resolved"},
    )
    import asyncio
    result = asyncio.run(result)

    assert clients == [{
        "brasaland": {
            "transport": "streamable_http",
            "url": "https://mcp.example.test/mcp",
            "headers": {"Authorization": "Bearer oauth-access-token"},
        }
    }]
    assert result["answer"] == '{"id": "incident-12", "status": "resolved"}'
    assert [step["node"] for step in result["trace"]] == ["receive_question", "mcp_tool"]
    assert result["trace"][-1]["tool"] == "update_incident_status"


def test_agent_routes_normal_questions_to_rag_without_mcp(monkeypatch):
    monkeypatch.setattr(agent_graph, "MultiServerMCPClient", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("MCP should not run for RAG query")))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: [{"text": "La política de residuos de Brasaland."}])
    monkeypatch.setattr(
        agent_graph,
        "_generate_structured_response",
        lambda question, context, memories: ("La política de residuos de Brasaland.", None),
    )

    import asyncio
    result = asyncio.run(agent_graph.query_agent("¿Cuál es la política de residuos?"))

    assert result["answer"] == "La política de residuos de Brasaland."
    assert [step["node"] for step in result["trace"]] == ["receive_question", "retrieve_context", "generate_answer"]
