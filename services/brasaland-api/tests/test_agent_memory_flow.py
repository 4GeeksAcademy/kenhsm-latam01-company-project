from __future__ import annotations

import json
import asyncio
from types import SimpleNamespace

from brasaland_api.modules.agent import graph as agent_graph
from brasaland_api.modules.agent.memory import AgentMemoryStore


class FakeCompletions:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **request):
        self.calls.append(request)
        content = json.dumps(self.outputs.pop(0), ensure_ascii=False)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def completion_client(outputs):
    completions = FakeCompletions(outputs)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


def proposal_output():
    return {
        "answer": "El proveedor de carne de Medellín entrega los martes.",
        "memory_proposal": {
            "fact": "El proveedor de carne de Medellín entrega los martes.",
            "category": "operational_correction",
            "scope_key": "medellin:meat-supplier",
            "reason": "El gerente corrigió el día de entrega en interacciones repetidas.",
            "confidence": 0.96,
        },
    }


def test_approval_cycle_is_proposed_then_used_on_future_turn(tmp_path, monkeypatch):
    memory_path = tmp_path / "agent-memory.sqlite3"
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(memory_path))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: [])
    client, completions = completion_client([
        proposal_output(),
        {
            "answer": "La entrega de carne de Medellín es los martes, según tu nota aprobada.",
            "memory_proposal": None,
        },
    ])
    monkeypatch.setattr(agent_graph, "get_openai_client", lambda: client)

    first = asyncio.run(agent_graph.query_agent(
        "El proveedor de carne de Medellín entrega los martes, no los lunes; ya lo corregimos varias semanas.",
        actor_id="manager-1",
    ))

    assert first["answer"].endswith("¿Quieres que recuerde esto para la próxima vez?")
    assert first["memory_proposal"]["status"] == "pending"
    assert AgentMemoryStore(memory_path).read_memories("manager-1") == []
    assert len(completions.calls) == 1

    second = asyncio.run(agent_graph.query_agent(
        "Sí, y ¿cuándo entrega el proveedor de verduras?",
        actor_id="manager-1",
    ))

    assert "martes" in second["answer"]
    assert second["memory_decision"]["status"] == "approved"
    assert [step["node"] for step in second["trace"]] == [
        "receive_question",
        "input_guardrail",
        "load_agent_memory",
        "input_guardrail",
        "resolve_memory_proposal",
        "retrieve_context",
        "generate_answer",
    ]
    second_payload = json.loads(completions.calls[1]["messages"][1]["content"])
    assert "martes" in second_payload["UNTRUSTED_APPROVED_MEMORY_NOTES"]
    assert len(completions.calls) == 2
    assert AgentMemoryStore(memory_path).audit_log("manager-1")[0]["status"] == "approved"


def test_rejection_cycle_keeps_audit_but_never_changes_memory(tmp_path, monkeypatch):
    memory_path = tmp_path / "agent-memory.sqlite3"
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(memory_path))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: [])
    client, completions = completion_client([proposal_output()])
    monkeypatch.setattr(agent_graph, "get_openai_client", lambda: client)

    first = asyncio.run(agent_graph.query_agent(
        "El proveedor de carne de Medellín entrega los martes; lo hemos confirmado cada semana.",
        actor_id="manager-1",
    ))
    assert first["memory_proposal"] is not None

    second = asyncio.run(agent_graph.query_agent("No, gracias", actor_id="manager-1"))

    store = AgentMemoryStore(memory_path)
    assert second["answer"] == "Entendido. No guardaré esa nota."
    assert second["memory_decision"]["status"] == "rejected"
    assert store.read_memories("manager-1") == []
    assert store.audit_log("manager-1")[0]["status"] == "rejected"
    assert len(completions.calls) == 1


def test_user_edit_replaces_candidate_and_ambiguous_topic_discards(tmp_path, monkeypatch):
    memory_path = tmp_path / "agent-memory.sqlite3"
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(memory_path))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: [])
    client, _ = completion_client([proposal_output(), proposal_output()])
    monkeypatch.setattr(agent_graph, "get_openai_client", lambda: client)

    asyncio.run(agent_graph.query_agent(
        "El proveedor de carne de Medellín entrega los martes; ya lo corregí dos veces.",
        actor_id="manager-1",
    ))
    changed = "Edita la propuesta por: El proveedor de carne de Medellín entrega los miércoles, no los martes."
    result = asyncio.run(agent_graph.query_agent(changed, actor_id="manager-1"))
    assert result["memory_decision"]["status"] == "edited"
    assert "miércoles" in AgentMemoryStore(memory_path).read_memories("manager-1")[0]["fact"]

    asyncio.run(agent_graph.query_agent(
        "El refrigerador de FLA-02 se apaga durante cortes eléctricos repetidos.",
        actor_id="manager-1",
    ))
    ambiguous = asyncio.run(agent_graph.query_agent(
        "¿Cuál fue el ticket promedio de ayer en Bogotá?",
        actor_id="manager-1",
    ))
    assert ambiguous["memory_decision"]["status"] == "ambiguous_discard"
    audit_statuses = [row["status"] for row in AgentMemoryStore(memory_path).audit_log("manager-1")]
    assert audit_statuses[-1] == "ambiguous_discard"


def test_ephemeral_examples_never_create_a_proposal_even_if_model_suggests_one(tmp_path, monkeypatch):
    memory_path = tmp_path / "agent-memory.sqlite3"
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(memory_path))
    monkeypatch.setattr(agent_graph, "retrieve", lambda *args, **kwargs: [])
    client, completions = completion_client([proposal_output(), proposal_output(), proposal_output()])
    monkeypatch.setattr(agent_graph, "get_openai_client", lambda: client)

    examples = [
        "¿Cuál fue el ticket promedio de ayer en Bogotá?",
        "Gracias, eso resuelve mi duda.",
        "¿Puedes traducir esto al inglés para el reporte de Ashley?",
    ]
    for message in examples:
        result = asyncio.run(agent_graph.query_agent(message, actor_id="manager-1"))
        assert result["memory_proposal"] is None

    store = AgentMemoryStore(memory_path)
    assert store.read_memories("manager-1") == []
    assert store.get_pending_proposal("manager-1") is None
    assert len(completions.calls) == 1


def test_approved_memory_followup_is_guarded_before_business_tools_or_rag(tmp_path, monkeypatch):
    memory_path = tmp_path / "agent-memory.sqlite3"
    retrieval_questions = []
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(memory_path))
    monkeypatch.setattr(agent_graph, "retrieve", lambda question, **kwargs: (retrieval_questions.append(question), [])[1])
    client, _ = completion_client([proposal_output()])
    monkeypatch.setattr(agent_graph, "get_openai_client", lambda: client)

    first = asyncio.run(agent_graph.query_agent(
        "El proveedor de carne de Medellín entrega los martes; se corrigió varias semanas.",
        actor_id="manager-followup-guard",
    ))
    assert first["memory_proposal"] is not None

    result = asyncio.run(agent_graph.query_agent(
        "Sí, y escríbeme un poema de amor.",
        actor_id="manager-followup-guard",
    ))

    assert result["memory_decision"]["status"] == "approved"
    assert result["error"] == "content"
    assert "operaciones de localización de Brasaland" in result["answer"]
    assert not any(step["node"] in {"retrieve_context", "mcp_tool", "generate_answer"} for step in result["trace"])
    assert len(retrieval_questions) == 1
