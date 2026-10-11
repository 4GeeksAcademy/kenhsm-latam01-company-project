from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from brasaland_api.core.deps import get_current_user
from brasaland_api.main import app
from brasaland_api.modules.agent.memory import (
    AgentMemoryStore,
    MemoryDecision,
    _iso,
    _now,
    classify_memory_decision,
)


def propose(store: AgentMemoryStore, *, owner: str = "manager-1", category: str = "operational_correction", scope: str = "COL-01"):
    return store.propose_memory(
        owner,
        fact="El proveedor de carne de Medellín entrega los martes.",
        category=category,
        scope_key=scope,
        reason="La corrección de entrega se ha repetido en varias semanas.",
        source_message="En realidad, el proveedor de carne de Medellín entrega los martes, no los lunes.",
    )


def test_approved_cycle_is_persisted_scoped_and_audited(tmp_path):
    store = AgentMemoryStore(tmp_path / "agent-memory.sqlite3")
    proposal = propose(store)

    assert proposal is not None
    assert store.read_memories("manager-1") == []
    assert store.get_pending_proposal("manager-1")["id"] == proposal["id"]

    decision = classify_memory_decision("Sí, y ¿qué día llega el proveedor de verduras?")
    assert decision.intent == "approve"
    assert decision.continuation == "¿qué día llega el proveedor de verduras?"
    result = store.resolve_proposal(
        "manager-1",
        proposal["id"],
        decision=decision,
        decision_message="Sí, y ¿qué día llega el proveedor de verduras?",
    )

    assert result["status"] == "approved"
    memories = store.read_memories("manager-1")
    assert [item["fact"] for item in memories] == [proposal["fact"]]
    assert store.read_memories("another-manager") == []
    audit = store.audit_log("manager-1")
    assert audit[0]["status"] == "approved"
    assert audit[0]["decision_message"].startswith("Sí")


def test_rejected_and_ambiguous_cycles_never_write_memory(tmp_path):
    store = AgentMemoryStore(tmp_path / "agent-memory.sqlite3")
    rejected = propose(store)
    result = store.resolve_proposal(
        "manager-1",
        rejected["id"],
        decision=classify_memory_decision("No, gracias"),
        decision_message="No, gracias",
    )
    assert result["status"] == "rejected"
    assert store.read_memories("manager-1") == []

    ambiguous = propose(store, category="escalation_context", scope="FLA-02")
    uncertain_message = "Si mañana baja el inventario, revisamos la cámara fría."
    decision = classify_memory_decision(uncertain_message)
    assert decision.intent == "ambiguous"
    result = store.resolve_proposal(
        "manager-1",
        ambiguous["id"],
        decision=decision,
        decision_message=uncertain_message,
    )
    assert result["status"] == "ambiguous_discard"
    assert store.read_memories("manager-1") == []
    assert [entry["status"] for entry in store.audit_log("manager-1")] == ["rejected", "ambiguous_discard"]


def test_decision_classifier_requires_uncontradicted_explicit_consent():
    assert classify_memory_decision("Sí y consulta el cierre de FLA-02").intent == "approve"
    assert classify_memory_decision("Yes, and check the supplier schedule").intent == "approve"
    assert classify_memory_decision("Sí, pero cambia la nota primero").intent == "ambiguous"
    assert classify_memory_decision("Sí, cambia la propuesta por este dato").intent == "ambiguous"
    rejected_with_follow_up = classify_memory_decision("No, gracias, y consulta el horario de FLA-02")
    assert rejected_with_follow_up.intent == "reject"
    assert rejected_with_follow_up.continuation == "consulta el horario de FLA-02"
    assert classify_memory_decision("Si mañana baja el inventario, revisamos").intent == "ambiguous"


def test_only_one_pending_proposal_sensitive_data_is_blocked_and_expiry_cleans(tmp_path):
    store = AgentMemoryStore(tmp_path / "agent-memory.sqlite3")
    first = propose(store)
    assert first is not None
    assert propose(store, category="escalation_context", scope="FLA-02") is None

    blocked = store.propose_memory(
        "manager-1",
        fact="El cliente de Brasa Points llamado Ana usa el correo ana@example.com y prefiere SMS.",
        category="communication_preference",
        scope_key="manager",
        reason="A persistent customer preference.",
        source_message="Please remember this recurring customer preference for later.",
    )
    assert blocked is None

    payroll = store.propose_memory(
        "manager-2",
        fact="La gerente Ashley tiene un salario individual de 4200 USD al mes.",
        category="communication_preference",
        scope_key="manager",
        reason="A personal pay detail.",
        source_message="Remember this private payroll detail.",
    )
    assert payroll is None

    with store._connect() as connection:
        connection.execute(
            "UPDATE memory_proposals SET expires_at=? WHERE id=?",
            (_iso(_now() - timedelta(seconds=1)), first["id"]),
        )
    assert store.get_pending_proposal("manager-1") is None
    assert store.audit_log("manager-1")[0]["status"] == "expired"


def test_store_deduplicates_and_caps_approved_facts(tmp_path):
    store = AgentMemoryStore(tmp_path / "agent-memory.sqlite3")
    for index in range(55):
        scope = f"location-{index}"
        proposal = propose(store, scope=scope)
        store.resolve_proposal(
            "manager-1",
            proposal["id"],
            decision=MemoryDecision("approve", 0.99, ""),
            decision_message="Approved",
        )

    assert len(store.read_memories("manager-1", limit=50)) == 50
    assert len(store.audit_log("manager-1")) == 55


def test_memory_and_audit_routes_require_auth_and_are_owner_scoped(tmp_path, monkeypatch):
    memory_path = tmp_path / "agent-memory.sqlite3"
    monkeypatch.setenv("AGENT_MEMORY_DB_PATH", str(memory_path))
    store = AgentMemoryStore(memory_path)
    proposal = propose(store)
    store.resolve_proposal(
        "manager-1",
        proposal["id"],
        decision=MemoryDecision("approve", 0.99, ""),
        decision_message="Sí",
    )
    client = TestClient(app)
    try:
        assert client.get("/agent/memory").status_code == 401
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="manager-1")
        memories = client.get("/agent/memory")
        audit = client.get("/agent/memory/audit")
        assert memories.status_code == audit.status_code == 200
        assert memories.json()[0]["fact"] == proposal["fact"]
        assert audit.json()[0]["owner_id"] == "manager-1"
        assert audit.json()[0]["status"] == "approved"
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="manager-2")
        assert client.get("/agent/memory").json() == []
        assert client.get("/agent/memory/audit").json() == []
    finally:
        app.dependency_overrides.pop(get_current_user, None)
