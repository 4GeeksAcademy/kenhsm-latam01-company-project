from __future__ import annotations

import asyncio
import copy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SERVICE_SRC = Path(__file__).resolve().parents[2] / "services" / "brasaland-api" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from brasaland_api.core.config import get_settings
from brasaland_api.modules.rfp_intake import approvals as approval_runtime
from data.pipelines.rfp_intake.approval import (
    MAX_APPROVAL_CHANGE_ITERATIONS,
    can_request_changes,
    detect_approval_conflicts,
    invoke_approval_branch,
    validate_human_response,
)
from data.pipelines.rfp_intake.drafting_adapter import run_rfp_draft_generation
from data.pipelines.rfp_intake.runtime import rfp_intake_graph


def _approval_state(ticket_id: str, approval_key: str, approver: str) -> dict:
    return {
        "ticket_id": ticket_id,
        "approval_key": approval_key,
        "approver": approver,
        "metadata": {"client_name": "Fixture Client"},
        "section": {"draft_content": "Proposal section", "evaluation_results": {"overall_pass": True}},
        "conflicts": [],
    }


def test_checkpointed_approval_resumes_without_restarting_and_keeps_other_branch_paused(tmp_path):
    checkpoint_path = str(tmp_path / "approval.sqlite3")
    marketing = invoke_approval_branch(
        checkpoint_path=checkpoint_path,
        ticket_id="ticket-parallel",
        approval_key="marketing",
        initial_state=_approval_state("ticket-parallel", "marketing", "Camila Ospina"),
    )
    operations = invoke_approval_branch(
        checkpoint_path=checkpoint_path,
        ticket_id="ticket-parallel",
        approval_key="operaciones",
        initial_state=_approval_state("ticket-parallel", "operaciones", "Felipe Guerrero"),
    )

    assert marketing["paused"] is True
    assert operations["paused"] is True
    assert marketing["trace"][0]["agent"] == "approval_request_builder"
    assert all({"agent", "input", "output", "timestamp"} <= event.keys() for event in marketing["trace"])

    approved_operations = invoke_approval_branch(
        checkpoint_path=checkpoint_path,
        ticket_id="ticket-parallel",
        approval_key="operaciones",
        response={"action": "approve"},
    )

    assert approved_operations["decision"]["approval_key"] == "operaciones"
    assert approved_operations["decision"]["action"] == "approve"
    resumed_marketing = invoke_approval_branch(
        checkpoint_path=checkpoint_path,
        ticket_id="ticket-parallel",
        approval_key="marketing",
        response={"action": "approve"},
    )
    assert resumed_marketing["decision"]["approval_key"] == "marketing"
    assert resumed_marketing["decision"]["action"] == "approve"


def test_response_validation_and_change_iteration_limit():
    assert validate_human_response({"action": "approve"}) == {"action": "approve", "comment": ""}
    assert validate_human_response({"action": "request_changes", "comment": "Ajustar alcance"})["action"] == "request_changes"
    for response in ({"action": "unknown"}, {"action": "request_changes"}):
        try:
            validate_human_response(response)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid human response was accepted")

    assert MAX_APPROVAL_CHANGE_ITERATIONS == 3
    assert can_request_changes(2) is True
    assert can_request_changes(3) is False


def test_rejection_and_request_changes_are_valid_resumed_graph_decisions(tmp_path):
    checkpoint_path = str(tmp_path / "decisions.sqlite3")
    for ticket_id, response in (
        ("ticket-rejected", {"action": "reject", "comment": "No cumple el alcance."}),
        ("ticket-changes", {"action": "request_changes", "comment": "Ajustar precio y alcance."}),
    ):
        invoke_approval_branch(
            checkpoint_path=checkpoint_path,
            ticket_id=ticket_id,
            approval_key="marketing",
            initial_state=_approval_state(ticket_id, "marketing", "Camila Ospina"),
        )
        resumed = invoke_approval_branch(
            checkpoint_path=checkpoint_path,
            ticket_id=ticket_id,
            approval_key="marketing",
            response=response,
        )
        assert resumed["decision"]["action"] == response["action"]


def test_fixed_arbitration_detects_structured_cost_sla_and_ceo_triggers():
    metadata = {
        "annual_estimated_value_usd": 60_000,
        "budget_range": "USD 60,000 per year",
        "scope": ["12 months"],
    }
    sections = [
        {"department_id": "operaciones", "evaluation_results": {"commercial_terms": {"price_per_event_usd": 85}, "compliance": {"violations": []}}},
        {"department_id": "procurement", "evaluation_results": {"commercial_terms": {"cost_per_event_usd": 100}, "compliance": {"violations": []}}},
        {"department_id": "training", "evaluation_results": {"commercial_terms": {"setup_lead_time_business_days": 5}, "compliance": {"violations": []}}},
    ]

    conflicts = detect_approval_conflicts(metadata, sections, {})

    assert {item["trigger_id"] for item in conflicts} == {"cost-vs-feasibility", "setup-sla-breach", "ceo-threshold"}
    assert next(item for item in conflicts if item["trigger_id"] == "cost-vs-feasibility")["owner"] == "Camila Ospina"
    assert next(item for item in conflicts if item["trigger_id"] == "setup-sla-breach")["owner"] == "Camila Ospina"
    assert next(item for item in conflicts if item["trigger_id"] == "ceo-threshold")["owner"] == "Mariana Restrepo"


def test_change_request_limit_marks_ticket_for_human_review(tmp_path, monkeypatch):
    ticket_id = "ticket-change-limit"
    monkeypatch.setenv("RFP_CHECKPOINT_PATH", str(tmp_path / "change-limit.sqlite3"))
    get_settings.cache_clear()
    section = {"department_id": "marketing", "approval_status": "pendiente", "draft_content": "Draft", "evaluation_results": {}}
    ticket = {
        "ticket_id": ticket_id,
        "status": "esperando_aprobación",
        "metadata": {"departments_needed": ["marketing"]},
        "department_sections": [section],
        "handoff_payload": {"departments_needed": ["marketing"], "approval_change_iterations": {"marketing": MAX_APPROVAL_CHANGE_ITERATIONS}},
    }
    approvals = {"marketing": {"approval_key": "marketing", "approval_status": "pendiente", "revision": 1}}
    updates = []
    invoke_approval_branch(
        checkpoint_path=str(tmp_path / "change-limit.sqlite3"),
        ticket_id=ticket_id,
        approval_key="marketing",
        initial_state=_approval_state(ticket_id, "marketing", "Camila Ospina"),
    )
    monkeypatch.setattr(approval_runtime.storage, "get_ticket", lambda _ticket_id: copy.deepcopy(ticket))
    monkeypatch.setattr(approval_runtime.storage, "list_approvals", lambda _ticket_id: list(approvals.values()))
    monkeypatch.setattr(approval_runtime.storage, "save_approval", lambda _ticket_id, key, values: approvals.update({key: {"approval_key": key, **values}}))
    monkeypatch.setattr(approval_runtime.storage, "update_draft_section", lambda _ticket_id, value: updates.append(copy.deepcopy(value)))
    monkeypatch.setattr(approval_runtime.storage, "update_ticket", lambda _ticket_id, values: ticket.update(copy.deepcopy(values)))
    monkeypatch.setattr(approval_runtime.storage, "persist_execution_events", lambda *_args: None)
    monkeypatch.setattr(approval_runtime, "generate_department_draft", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("iteration cap must prevent generation")))

    status = approval_runtime.respond_to_approval(
        ticket_id,
        "marketing",
        "Camila Ospina",
        {"action": "request_changes", "comment": "Cambiar las condiciones."},
    )

    assert status == "needs_human_review"
    assert ticket["status"] == "needs_human_review"
    assert approvals["marketing"]["approval_status"] == "rechazado"


def test_seeded_part_one_to_part_three_end_to_end_with_simulated_human_resumes(tmp_path, monkeypatch):
    try:
        from brasaland_api.modules.rfp_intake import router as rfp_router
    except ModuleNotFoundError as error:
        if error.name == "fastapi":
            pytest.skip("El E2E de API requiere el entorno de services/brasaland-api.")
        raise

    ticket_id = "ticket-e2e-approval"
    markdown = (
        "Andes Tech Solutions requests weekly catering for 220 employees in Medellin. "
        "The 12-month contract uses the standard menu and has an annual budget of USD 60,000."
    )
    intake = rfp_intake_graph.invoke({"ticket_id": ticket_id, "markdown": markdown})
    assert intake["classification"]["is_valid"] is True
    assert intake["departments_needed"] == ["marketing", "operaciones", "procurement"]

    metadata = {**intake["metadata"], "budget_range": "USD 60,000 per year", "annual_estimated_value_usd": 60_000}
    handoff = {**intake["handoff_payload"], "metadata": metadata}
    monkeypatch.setenv("RFP_CHECKPOINT_PATH", str(tmp_path / "e2e-checkpoints.sqlite3"))
    get_settings.cache_clear()
    monkeypatch.setattr("data.pipelines.rfp_intake.drafting.get_openai_client", lambda: None)
    drafted = asyncio.run(run_rfp_draft_generation(
        ticket_id=ticket_id,
        metadata=metadata,
        handoff_payload=handoff,
        department_sections=intake["department_results"],
    ))
    sections = []
    for source in intake["department_results"]:
        sections.append({**source, **drafted["sections"][source["department_id"]]})
    part_three_metadata = dict(metadata)
    part_three_metadata.pop("budget_range")
    part_three_handoff = dict(drafted["handoff_payload"])
    part_three_handoff.pop("required_approvals", None)
    drafted = {**drafted, "handoff_payload": {**part_three_handoff, "metadata": part_three_metadata}}
    ticket = {
        "ticket_id": ticket_id,
        "status": "analizando",
        "metadata": None,
        "department_sections": [],
        "handoff_payload": None,
    }
    approvals: dict[str, dict] = {}
    events: list[dict] = []
    final_documents: dict[str, dict] = {}
    persisted_ticket = copy.deepcopy(ticket)

    def get_ticket(_ticket_id):
        return copy.deepcopy(persisted_ticket) if _ticket_id == ticket_id else None

    def update_ticket(_ticket_id, values):
        persisted_ticket.update(copy.deepcopy(values))

    def update_draft_section(_ticket_id, section):
        for index, current in enumerate(persisted_ticket["department_sections"]):
            if current["department_id"] == section["department_id"]:
                persisted_ticket["department_sections"][index] = copy.deepcopy(section)
                return
        raise AssertionError("section not found")

    def persist_analysis(_ticket_id, saved_metadata, saved_sections):
        persisted_ticket["metadata"] = copy.deepcopy(saved_metadata)
        persisted_ticket["department_sections"] = copy.deepcopy(saved_sections)

    def persist_draft_sections(_ticket_id, saved_sections):
        for saved in saved_sections:
            for index, current in enumerate(persisted_ticket["department_sections"]):
                if current["department_id"] == saved["department_id"]:
                    persisted_ticket["department_sections"][index] = {**current, **copy.deepcopy(saved)}

    def save_approval(_ticket_id, key, values):
        approvals[key] = {"approval_key": key, **copy.deepcopy(values)}

    def list_approvals(_ticket_id):
        return [copy.deepcopy(item) for item in approvals.values()]

    def persist_events(_ticket_id, rows):
        events.extend(copy.deepcopy(rows))

    def save_final(document):
        final_documents[document["ticket_id"]] = copy.deepcopy(document)

    monkeypatch.setattr(approval_runtime.storage, "get_ticket", get_ticket)
    monkeypatch.setattr(approval_runtime.storage, "update_ticket", update_ticket)
    monkeypatch.setattr(approval_runtime.storage, "update_draft_section", update_draft_section)
    monkeypatch.setattr(approval_runtime.storage, "save_approval", save_approval)
    monkeypatch.setattr(approval_runtime.storage, "list_approvals", list_approvals)
    monkeypatch.setattr(approval_runtime.storage, "persist_execution_events", persist_events)
    monkeypatch.setattr(approval_runtime.storage, "persist_final_document", save_final)
    monkeypatch.setattr(approval_runtime.storage, "persist_analysis", persist_analysis)
    monkeypatch.setattr(approval_runtime.storage, "persist_draft_sections", persist_draft_sections)

    intake_result = {**intake, "metadata": part_three_metadata, "handoff_payload": {**part_three_handoff, "metadata": part_three_metadata}}
    monkeypatch.setattr(rfp_router, "run_rfp_intake", lambda *_args: intake_result)
    rfp_router.process_rfp_ticket(ticket_id, "fixture/request.pdf")
    assert persisted_ticket["status"] == "analisis_completo"
    persisted_ticket["status"] = "generando_borrador"

    async def draft_generation(**_kwargs):
        _kwargs["progress_callback"](list(drafted["sections"].values()), drafted["handoff_payload"])
        return drafted

    monkeypatch.setattr(rfp_router, "run_rfp_draft_generation", draft_generation)
    rfp_router.process_rfp_draft_ticket(ticket_id)

    assert persisted_ticket["status"] == "esperando_aprobación"
    assert approvals["marketing"]["approval_status"] == "pendiente"
    assert approvals["ceo"]["approval_status"] == "pendiente"

    status = approval_runtime.respond_to_approval(ticket_id, "operaciones", "Felipe Guerrero", {
        "action": "approve",
        "price_per_event_usd": 80,
        "setup_lead_time_business_days": 10,
    })
    assert status == "esperando_aprobación"
    assert approvals["marketing"]["approval_status"] == "pendiente"

    try:
        approval_runtime.respond_to_approval(ticket_id, "procurement", "Lucía Fernández", {
            "action": "approve",
            "cost_per_event_usd": 100,
            "setup_lead_time_business_days": 10,
        })
    except ValueError as error:
        assert "conflictos de arbitraje" in str(error)
    else:
        raise AssertionError("cost-vs-feasibility must block procurement sign-off")
    assert any(item["trigger_id"] == "cost-vs-feasibility" for item in persisted_ticket["handoff_payload"]["approval_workflow"]["conflicts"])

    status = approval_runtime.respond_to_approval(ticket_id, "procurement", "Lucía Fernández", {
        "action": "request_changes",
        "comment": "Ajustar el costo para que el precio por evento sea viable.",
        "cost_per_event_usd": 70,
        "setup_lead_time_business_days": 10,
    })
    assert status == "esperando_aprobación"
    assert approvals["procurement"]["revision"] == 2

    for key, approver in (("marketing", "Camila Ospina"), ("procurement", "Lucía Fernández"), ("ceo", "Mariana Restrepo")):
        status = approval_runtime.respond_to_approval(ticket_id, key, approver, {"action": "approve"})

    assert status == "terminado"
    assert persisted_ticket["status"] == "terminado"
    assert final_documents[ticket_id]["sections"]
    assert "Andes Tech Solutions" in final_documents[ticket_id]["document_markdown"]
    assert all("evaluation_results" not in section for section in final_documents[ticket_id]["sections"])
    assert {"rfp_classifier", "rfp_metadata_extractor", "department_generator:operaciones", "parallel_evaluators:operaciones", "ultimate_document_synthesizer"} <= {event["agent"] for event in events}
    assert all({"agent", "input", "output", "timestamp"} <= event.keys() for event in events)
