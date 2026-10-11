from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_SRC = ROOT / "services" / "brasaland-api" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from brasaland_api.modules.agent.graph import build_agent_graph


def test_langgraph_trace_runs_retrieve_before_generate(monkeypatch):
    trace_events = []

    def fake_retrieve(question, *, k=5, min_score=0.35):
        trace_events.append(("retrieve", question))
        return [
            {
                "company": "brasaland",
                "source_document": "brasaland-loyalty-program.es.md",
                "section": "Programa de lealtad",
                "language": "es",
                "chunk_index": 0,
                "text": "Los clientes ganan Brasa Points al comprar con tarjeta.",
            }
        ]

    def fake_generate(question, context):
        trace_events.append(("generate", question, len(context)))
        return "Con tarjeta puedes ganar Brasa Points."

    monkeypatch.setattr("brasaland_api.modules.agent.graph.retrieve", fake_retrieve)
    monkeypatch.setattr("brasaland_api.modules.agent.graph.generate_answer", fake_generate)

    graph = build_agent_graph()
    result = graph.invoke({"question": "¿Cómo ganan puntos?"}, config={"configurable": {"thread_id": "trace-order"}})

    assert result["answer"] == "Con tarjeta puedes ganar Brasa Points."
    assert [event[0] for event in trace_events] == ["retrieve", "generate"]
    assert result["trace"][0]["node"] == "receive_question"
    assert result["trace"][-1]["node"] == "generate_answer"


def test_langgraph_empty_question_uses_honest_error_path(monkeypatch):
    monkeypatch.setattr("brasaland_api.modules.agent.graph.retrieve", lambda *args, **kwargs: [])

    graph = build_agent_graph()
    result = graph.invoke({"question": "   "}, config={"configurable": {"thread_id": "empty-question"}})

    assert "No tengo información suficiente" in result["answer"]
    assert [step["node"] for step in result["trace"]] == ["receive_question", "respond_without_context"]


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
    monkeypatch.setattr("brasaland_api.modules.agent.graph.generate_answer", fake_generate)

    graph = build_agent_graph()
    result = graph.invoke({"question": "¿Cómo se separan los residuos orgánicos?"}, config={"configurable": {"thread_id": "anchored-context"}})

    assert result["answer"] == "Los residuos orgánicos deben separarse de los reciclables en cada local."
    assert any(step["node"] == "retrieve_context" for step in result["trace"])
    assert any(step["node"] == "generate_answer" for step in result["trace"])
