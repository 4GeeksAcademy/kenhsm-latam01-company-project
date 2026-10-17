from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_SRC = ROOT / "services" / "brasaland-api" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from brasaland_api.modules.agent import graph as agent_graph
from brasaland_api.modules.agent.graph import build_agent_graph
from brasaland_api.modules.agent.incident_tools import IncidentLookupOutput
from brasaland_api.modules.incidents.schemas import IncidentOut


def test_langgraph_trace_runs_retrieve_before_generate(monkeypatch):
    trace_events = []

    def fake_retrieve(question, *, k=5, min_score=0.35):
        trace_events.append(("retrieve", question))
        return [
            {
                "company": "brasaland",
                "source_document": "brasaland-waste-protocol.es.md",
                "section": "Procedimientos del turno",
                "language": "es",
                "chunk_index": 0,
                "text": "Antes de abrir, revisa las temperaturas y separa los residuos orgánicos.",
            }
        ]

    def fake_generate(question, context):
        trace_events.append(("generate", question, len(context)))
        return "Antes de abrir, revisa las temperaturas y separa los residuos orgánicos."

    monkeypatch.setattr("brasaland_api.modules.agent.graph.retrieve", fake_retrieve)
    monkeypatch.setattr(
        "brasaland_api.modules.agent.graph._generate_structured_response",
        lambda question, context, memories, **kwargs: (fake_generate(question, context), None),
    )

    graph = build_agent_graph()
    result = graph.invoke({"question": "¿Qué debo revisar antes de abrir el local?"}, config={"configurable": {"thread_id": "trace-order"}})

    assert result["answer"] == "Antes de abrir, revisa las temperaturas y separa los residuos orgánicos."
    assert [event[0] for event in trace_events] == ["retrieve", "generate"]
    assert result["trace"][0]["node"] == "receive_question"
    assert result["trace"][1]["node"] == "input_guardrail"
    assert result["trace"][-1]["node"] == "generate_answer"


def test_langgraph_empty_question_uses_honest_error_path(monkeypatch):
    monkeypatch.setattr("brasaland_api.modules.agent.graph.retrieve", lambda *args, **kwargs: [])

    graph = build_agent_graph()
    result = graph.invoke({"question": "   "}, config={"configurable": {"thread_id": "empty-question"}})

    assert "No tengo información suficiente" in result["answer"]
    assert [step["node"] for step in result["trace"]] == ["receive_question", "input_guardrail", "source_routing", "respond_without_context"]


def test_langgraph_keeps_answer_anclado_al_contexto(monkeypatch):
    expected_context = [
        {
            "company": "brasaland",
            "source_document": "brasaland-waste-protocol.es.md",
            "section": "Manejo de residuos",
            "language": "es",
            "chunk_index": 0,
            "text": "Los residuos orgánicos deben separarse de los reciclables en cada local.",
        }
    ]

    def fake_retrieve(question, *, k=5, min_score=0.35):
        return expected_context

    def fake_generate(question, context):
        assert context == expected_context
        return "Los residuos orgánicos deben separarse de los reciclables en cada local."

    monkeypatch.setattr("brasaland_api.modules.agent.graph.retrieve", fake_retrieve)
    monkeypatch.setattr(
        "brasaland_api.modules.agent.graph._generate_structured_response",
        lambda question, context, memories, **kwargs: (fake_generate(question, context), None),
    )

    graph = build_agent_graph()
    result = graph.invoke({"question": "¿Cómo se separan los residuos orgánicos?"}, config={"configurable": {"thread_id": "anchored-context"}})

    assert result["answer"] == "Los residuos orgánicos deben separarse de los reciclables en cada local."
    assert result["trace"][1]["node"] == "input_guardrail"
    assert any(step["node"] == "retrieve_context" for step in result["trace"])
    assert any(step["node"] == "generate_answer" for step in result["trace"])


def _incident_lookup_result(incident_id: str) -> IncidentLookupOutput:
    now = datetime.now(timezone.utc)
    return IncidentLookupOutput(
        found=True,
        incident=IncidentOut(
            id=incident_id,
            title="Falla de equipo",
            description="La nevera de la cocina no enfría.",
            category="equipment_failure",
            status="in_progress",
            origin="branch",
            branch="medellin_centro",
            created_at=now,
            updated_at=now,
        ),
    )


def test_routing_evaluation_ticket_question_uses_live_incident_tool_only(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(tmp_path / "memory.sqlite3"))
    monkeypatch.setattr(agent_graph, "lookup_incident_record", lambda payload: _incident_lookup_result(payload.incident_id))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("ticket lookup must not use RAG")))
    generated_context = []

    def generate(question, context, memories, **kwargs):
        generated_context.extend(context)
        return "El ticket 482 está en progreso.", None

    monkeypatch.setattr(agent_graph, "_generate_structured_response", generate)
    result = asyncio.run(agent_graph.query_agent("¿En qué estado está el ticket 482?", actor_id="manager-482"))

    assert result["answer"] == "El ticket 482 está en progreso."
    assert generated_context[0]["source_document"] == "Live incident manager lookup"
    assert [step["node"] for step in result["trace"]][-3:] == ["source_routing", "incident_lookup", "generate_answer"]
    assert result["trace"][3]["sources"] == ["incident_tool"]


def test_routing_evaluation_procedure_question_uses_rag_without_tools(monkeypatch):
    monkeypatch.setattr(agent_graph, "lookup_incident_record", lambda *args: (_ for _ in ()).throw(AssertionError("RAG question must not call incident service")))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: [{"source_document": "brasaland-waste-protocol.es.md", "text": "Separa los residuos orgánicos."}])
    monkeypatch.setattr(agent_graph, "_generate_structured_response", lambda *args, **kwargs: ("Separa los residuos orgánicos.", None))

    result = asyncio.run(agent_graph.query_agent("¿Cuál es el procedimiento de separación de residuos?"))

    assert result["answer"] == "Separa los residuos orgánicos."
    assert result["trace"][2]["node"] == "source_routing"
    assert result["trace"][2]["sources"] == ["rag"]
    assert [step["node"] for step in result["trace"]][-2:] == ["retrieve_context", "generate_answer"]


def test_routing_evaluation_combines_incident_tool_then_rag(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(tmp_path / "memory.sqlite3"))
    monkeypatch.setattr(agent_graph, "lookup_incident_record", lambda payload: _incident_lookup_result(payload.incident_id))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: [{"source_document": "incident-procedure", "text": "Escala la falla al gerente de turno."}])
    monkeypatch.setattr(agent_graph, "_generate_structured_response", lambda question, context, memories, **kwargs: ("El ticket está en progreso; escala la falla al gerente de turno.", None))

    result = asyncio.run(agent_graph.query_agent(
        "¿Cuál es el estado del ticket 482 y qué protocolo debo seguir?",
        actor_id="manager-mixed",
    ))

    assert result["trace"][3]["sources"] == ["incident_tool", "rag"]
    assert [step["node"] for step in result["trace"]][-3:] == ["incident_lookup", "retrieve_context", "generate_answer"]


def test_incident_lookup_missing_record_uses_honest_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(tmp_path / "memory.sqlite3"))
    monkeypatch.setattr(agent_graph, "lookup_incident_record", lambda payload: IncidentLookupOutput(found=False))
    monkeypatch.setattr(agent_graph, "_generate_structured_response", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("missing ticket must not be generated")))

    result = asyncio.run(agent_graph.query_agent("¿En qué estado está el ticket 99999?", actor_id="manager-missing"))

    assert result["error"] == "INCIDENT_NOT_FOUND"
    assert result["answer"] == "No encontré ese ticket en el gestor de incidencias."
    assert result["trace"][-1]["node"] == "incident_lookup_fallback"

def test_incident_lookup_timeout_uses_honest_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(tmp_path / "memory.sqlite3"))
    monkeypatch.setattr(agent_graph, "INCIDENT_LOOKUP_TIMEOUT_SECONDS", 0.01)

    async def never_finishes(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(agent_graph.asyncio, "to_thread", never_finishes)
    result = asyncio.run(agent_graph.query_agent("¿En qué estado está el ticket 482?", actor_id="manager-timeout"))

    assert result["error"] == "INCIDENT_LOOKUP_TIMEOUT"
    assert result["answer"] == "No pude confirmar el estado de ese ticket ahora mismo."
    lookup_trace = next(step for step in result["trace"] if step["node"] == "incident_lookup")
    assert lookup_trace["timeout_seconds"] == 0.01
