from __future__ import annotations

from fastapi.testclient import TestClient

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.agent import router as agent_router
from brasaland_api.main import app
from brasaland_api.modules.agent.incident_tools import IncidentLookupInput, lookup_incident
from brasaland_api.modules.incidents import services


def test_incidents_manager_requires_api_authentication():
    client = TestClient(app)

    response = client.get("/api/incidents")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

    tool_response = client.post(
        "/agent/query",
        json={
            "question": "Actualiza una incidencia",
            "tool_action": "update_incident_status",
            "tool_arguments": {"incident_id": "incident-1", "status": "resolved"},
        },
    )
    assert tool_response.status_code == 401


def test_incidents_manager_create_get_and_lifecycle_transition():
    app.dependency_overrides[get_current_user] = lambda: object()
    client = TestClient(app)
    try:
        created = client.post(
            "/api/incidents",
            json={
                "title": "Refrigerador sin temperatura estable",
                "description": "El refrigerador de cocina no mantiene temperatura estable.",
                "category": "equipment_failure",
                "status": "open",
                "origin": "branch",
                "branch": "medellin_centro",
            },
        )
        assert created.status_code == 201
        incident_id = created.json()["id"]

        fetched = client.get(f"/api/incidents/{incident_id}")
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "open"

        transitioned = client.patch(
            f"/api/incidents/{incident_id}/status",
            json={"status": "in_progress"},
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "in_progress"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

def test_typed_agent_lookup_reads_existing_incidents_by_id_and_source_key():
    incident = services.create_incident(
        {
            "title": "Refrigerador sin temperatura estable",
            "description": "El refrigerador de cocina no mantiene temperatura estable.",
            "category": "equipment_failure",
            "status": "open",
            "origin": "branch",
            "branch": "medellin_centro",
        },
        source_key="BRS-000482",
    )

    by_id = lookup_incident(IncidentLookupInput(incident_id=incident.id))
    by_source_key = lookup_incident(IncidentLookupInput(incident_id="BRS-000482"))

    assert by_id.found and by_source_key.found
    assert by_id.incident.id == incident.id
    assert by_source_key.incident.status == "open"
    assert by_source_key.incident.category == "equipment_failure"
    assert services.get_incident(incident.id).status == "open"


def test_rag_agent_endpoint_remains_public(monkeypatch):
    async def fake_query_agent(question, **kwargs):
        return {"answer": "RAG response", "trace": [], "error": None}

    monkeypatch.setattr(agent_router, "query_agent", fake_query_agent)
    response = TestClient(app).post("/agent/query", json={"question": "Consulta de conocimiento"})

    assert response.status_code == 200
    assert response.json()["answer"] == "RAG response"
