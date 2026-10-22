from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from brasaland_api.core.deps import get_current_user
from brasaland_api.main import app
from brasaland_api.modules.rfp_intake import storage
from brasaland_api.modules.rfp_intake.events import rfp_event_broker
from brasaland_api.modules.rfp_intake.router import process_rfp_draft_ticket, process_rfp_ticket, stream_rfp_events


def test_rfp_upload_requires_authentication():
    app.dependency_overrides.clear()
    client = TestClient(app)

    response = client.post("/rfp-intake", files={"file": ("request.pdf", b"%PDF-1.4", "application/pdf")})

    assert response.status_code == 401


def test_draft_generation_requires_authentication():
    app.dependency_overrides.clear()
    response = TestClient(app).post("/rfp-intake/ticket-1/generate-draft")

    assert response.status_code == 401


def test_rfp_event_stream_requires_authentication():
    app.dependency_overrides.clear()

    response = TestClient(app).get("/rfp-intake/events")

    assert response.status_code == 401


def test_rfp_event_stream_emits_named_json_sse_frame():
    async def read_frame():
        request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
        response = await stream_rfp_events(request)
        iterator = response.body_iterator
        connected_frame = await anext(iterator)
        payload = {
            "ticket_id": "tkt_0192",
            "rfp_id": "rfp_0088",
            "status": "analyzing",
            "created_at": "2026-10-22T14:32:00+00:00",
        }
        rfp_event_broker.publish(payload)
        event_frame = await anext(iterator)
        await iterator.aclose()
        return response, connected_frame, event_frame, payload

    response, connected_frame, event_frame, expected_payload = asyncio.run(read_frame())
    lines = event_frame.splitlines()

    assert response.headers["content-type"].startswith("text/event-stream")
    assert connected_frame == ": connected\n\n"
    assert lines[0] == "event: rfp_ticket_created"
    assert json.loads(lines[1].removeprefix("data: ")) == expected_payload


def test_department_approval_requires_authentication():
    app.dependency_overrides.clear()
    response = TestClient(app).post(
        "/rfp-intake/ticket-1/approvals/marketing",
        json={"action": "approve"},
    )

    assert response.status_code == 401


def test_approval_endpoint_uses_authenticated_profile_and_returns_ticket_state():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    try:
        with (
            patch("brasaland_api.modules.rfp_intake.router.profile_services.get_profile_by_user_id", return_value=SimpleNamespace(name="Camila Ospina")) as profile,
            patch("brasaland_api.modules.rfp_intake.router.respond_to_approval", return_value="esperando_aprobación") as respond,
        ):
            response = TestClient(app).post(
                "/rfp-intake/ticket-1/approvals/marketing",
                json={"action": "approve", "comment": "Revisado"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ticket_id": "ticket-1", "status": "esperando_aprobación"}
    profile.assert_called_once_with("user-1")
    respond.assert_called_once_with("ticket-1", "marketing", "Camila Ospina", {"action": "approve", "comment": "Revisado"})


def test_final_document_endpoint_is_unavailable_until_synthesis():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    try:
        with patch("brasaland_api.modules.rfp_intake.router.storage.get_final_document", return_value=None):
            response = TestClient(app).get("/rfp-intake/ticket-1/final-document")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_final_document_endpoint_returns_the_persisted_synthesis():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    document = {
        "ticket_id": "ticket-1",
        "document_markdown": "# Approved proposal",
        "sections": [{"department_id": "marketing", "draft_content": "Approved text"}],
        "total_estimated_value": 60_000,
        "currency": "USD",
        "generated_at": "2026-10-20T12:00:00Z",
    }
    try:
        with patch("brasaland_api.modules.rfp_intake.router.storage.get_final_document", return_value=document):
            response = TestClient(app).get("/rfp-intake/ticket-1/final-document")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == document


def test_upload_rejects_non_pdf_before_persisting():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    try:
        response = TestClient(app).post(
            "/rfp-intake",
            files={"file": ("request.txt", b"not a pdf", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415


def test_upload_persists_pdf_and_queues_background_pipeline(tmp_path):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    repository_root = tmp_path / "repository"
    raw_directory = repository_root / "data" / "raw" / "rfp-intake"
    try:
        with (
            patch("brasaland_api.modules.rfp_intake.router.REPOSITORY_ROOT", repository_root),
            patch("brasaland_api.modules.rfp_intake.router.RAW_RFP_DIRECTORY", raw_directory),
            patch("brasaland_api.modules.rfp_intake.router.storage.create_ticket") as create_ticket,
            patch("brasaland_api.modules.rfp_intake.router.process_rfp_ticket") as process_ticket,
        ):
            response = TestClient(app).post(
                "/rfp-intake",
                files={"file": ("request.pdf", b"%PDF-1.4 sample", "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    ticket_id = response.json()["ticket_id"]
    assert response.json()["status"] == "analizando"
    ticket = create_ticket.call_args.args[0]
    assert ticket["ticket_id"] == ticket_id
    assert ticket["raw_pdf_path"] == f"data/raw/rfp-intake/{ticket_id}.pdf"
    assert (raw_directory / f"{ticket_id}.pdf").read_bytes() == b"%PDF-1.4 sample"
    process_ticket.assert_called_once_with(
        ticket_id,
        str(raw_directory / f"{ticket_id}.pdf"),
        ticket["rfp_id"],
        ticket["created_at"],
    )


def test_ticket_get_returns_persisted_status_and_handoff():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    record = {
        "ticket_id": "ticket-1",
        "status": "analisis_completo",
        "metadata": {"client_name": "Andes Tech Solutions"},
        "department_sections": [],
        "handoff_payload": {"ticket_id": "ticket-1", "workstreams": []},
    }
    try:
        with patch("brasaland_api.modules.rfp_intake.router.storage.get_ticket", return_value=record):
            response = TestClient(app).get("/rfp-intake/ticket-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "analisis_completo"
    assert response.json()["handoff_payload"]["ticket_id"] == "ticket-1"


def test_ticket_list_supports_created_after_and_pagination():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    created_after = "2026-10-22T14:32:00+00:00"
    try:
        with patch("brasaland_api.modules.rfp_intake.router.storage.list_tickets", return_value=[]) as list_tickets:
            response = TestClient(app).get(
                "/rfp-intake",
                params={"limit": 50, "offset": 100, "created_after": created_after},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    list_tickets.assert_called_once_with(limit=50, offset=100, created_after=created_after)


def test_draft_generation_claims_only_complete_part_one_handoff():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    ticket = {
        "ticket_id": "ticket-1",
        "status": "analisis_completo",
        "handoff_payload": {"ticket_id": "ticket-1", "departments_needed": ["operaciones"]},
        "department_sections": [{"department_id": "operaciones", "key_aspects": {"focus": "capacidad"}}],
    }
    try:
        with (
            patch("brasaland_api.modules.rfp_intake.router.storage.get_ticket", return_value=ticket),
            patch("brasaland_api.modules.rfp_intake.router.storage.claim_draft_generation", return_value=True) as claim,
            patch("brasaland_api.modules.rfp_intake.router.profile_services.get_profile_by_user_id", return_value=SimpleNamespace(name="Camila Ospina")),
            patch("brasaland_api.modules.rfp_intake.router.process_rfp_draft_ticket") as process,
        ):
            response = TestClient(app).post("/rfp-intake/ticket-1/generate-draft")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {"ticket_id": "ticket-1", "status": "generando_borrador"}
    claim.assert_called_once_with("ticket-1", expected_status="analisis_completo")
    process.assert_called_once_with("ticket-1")


def test_draft_generation_reopens_ticket_after_human_review():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    ticket = {
        "ticket_id": "ticket-1",
        "status": "needs_human_review",
        "handoff_payload": {"ticket_id": "ticket-1", "departments_needed": ["marketing"]},
        "department_sections": [{"department_id": "marketing", "key_aspects": {}}],
    }
    try:
        with (
            patch("brasaland_api.modules.rfp_intake.router.storage.get_ticket", return_value=ticket),
            patch("brasaland_api.modules.rfp_intake.router.storage.claim_draft_generation", return_value=True) as claim,
            patch("brasaland_api.modules.rfp_intake.router.profile_services.get_profile_by_user_id", return_value=SimpleNamespace(name="Camila Ospina")),
            patch("brasaland_api.modules.rfp_intake.router.process_rfp_draft_ticket") as process,
        ):
            response = TestClient(app).post("/rfp-intake/ticket-1/generate-draft")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    claim.assert_called_once_with("ticket-1", expected_status="needs_human_review")
    process.assert_called_once_with("ticket-1")


def test_only_marketing_owner_can_reopen_rejected_rfp_generation():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    ticket = {
        "ticket_id": "ticket-1",
        "status": "needs_human_review",
        "handoff_payload": {"ticket_id": "ticket-1", "departments_needed": ["marketing"]},
        "department_sections": [{"department_id": "marketing", "key_aspects": {}}],
    }
    try:
        with (
            patch("brasaland_api.modules.rfp_intake.router.storage.get_ticket", return_value=ticket),
            patch("brasaland_api.modules.rfp_intake.router.profile_services.get_profile_by_user_id", return_value=SimpleNamespace(name="Felipe Guerrero")),
            patch("brasaland_api.modules.rfp_intake.router.storage.claim_draft_generation") as claim,
        ):
            response = TestClient(app).post("/rfp-intake/ticket-1/generate-draft")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    claim.assert_not_called()


def test_background_draft_generation_persists_progress_and_final_handoff():
    ticket = {
        "ticket_id": "ticket-1",
        "status": "generando_borrador",
        "metadata": {},
        "handoff_payload": {"ticket_id": "ticket-1", "departments_needed": ["operaciones"]},
        "department_sections": [{"department_id": "operaciones", "key_aspects": {}}],
    }
    section = {
        "department_id": "operaciones",
        "draft_content": "Draft text",
        "evaluation_results": {"overall_pass": False},
    }
    handoff = {"ticket_id": "ticket-1", "draft_generation": {"status": "needs_human_review"}}

    async def fake_generation(**kwargs):
        kwargs["status_callback"]("en_evaluación")
        kwargs["progress_callback"]([section], handoff)
        kwargs["status_callback"]("needs_human_review")
        return {
            "ticket_status": "needs_human_review",
            "sections": {"operaciones": section},
            "handoff_payload": handoff,
        }

    with (
        patch("brasaland_api.modules.rfp_intake.router.storage.get_ticket", return_value=ticket),
        patch("brasaland_api.modules.rfp_intake.router.storage.persist_draft_sections") as persist,
        patch("brasaland_api.modules.rfp_intake.router.storage.persist_execution_events"),
        patch("brasaland_api.modules.rfp_intake.router.storage.update_ticket") as update,
        patch("brasaland_api.modules.rfp_intake.router.initialize_approval_branches"),
        patch("brasaland_api.modules.rfp_intake.router.run_rfp_draft_generation", side_effect=fake_generation),
    ):
        process_rfp_draft_ticket("ticket-1")

    persist.assert_called_once_with("ticket-1", [section])
    saved_statuses = [call.args[1].get("status") for call in update.call_args_list]
    assert "en_evaluación" in saved_statuses
    assert "needs_human_review" in saved_statuses
    assert update.call_args_list[-1].args[1]["handoff_payload"] == handoff


def test_storage_claim_is_conditional_on_part_one_completion():
    with patch("brasaland_api.modules.rfp_intake.storage._request", return_value=[{"ticket_id": "ticket-1"}]) as request:
        assert storage.claim_draft_generation("ticket-1") is True

    assert request.call_args.kwargs["params"]["status"] == "eq.analisis_completo"
    assert request.call_args.kwargs["prefer"] == "return=representation"


def test_storage_persists_draft_content_and_structured_evaluation_by_department():
    section = {
        "department_id": "operaciones",
        "draft_content": "Draft text",
        "evaluation_results": {"readability": {"pass": True}, "overall_pass": True},
    }
    with patch("brasaland_api.modules.rfp_intake.storage._request", return_value=[{"department_id": "operaciones"}]) as request:
        storage.persist_draft_sections("ticket-1", [section])

    assert request.call_args.args[:2] == ("PATCH", "department_sections")
    assert request.call_args.kwargs["params"] == {
        "ticket_id": "eq.ticket-1",
        "department_id": "eq.operaciones",
    }
    assert request.call_args.kwargs["payload"]["draft_content"] == "Draft text"
    assert request.call_args.kwargs["payload"]["evaluation_results"] == section["evaluation_results"]


def test_persisted_department_aspects_include_the_named_contact():
    section = {
        "department_id": "operaciones",
        "department_name": "Operaciones de Restaurante",
        "contact": "Felipe Guerrero",
        "key_aspects": {"focus": "viabilidad operativa", "source_extracts": [], "open_questions": []},
    }
    with patch("brasaland_api.modules.rfp_intake.storage._request") as request:
        storage.persist_analysis("ticket-1", {"client_name": "Andes Tech Solutions"}, [section])

    saved_sections = request.call_args_list[1].kwargs["payload"]
    assert saved_sections[0]["key_aspects"]["contact"] == "Felipe Guerrero"
    assert saved_sections[0]["key_aspects"]["department_name"] == "Operaciones de Restaurante"


def test_background_pipeline_completes_with_synthesizer_handoff():
    result = {
        "classification": {"is_valid": True},
        "metadata": {"client_name": "Andes Tech Solutions"},
        "department_results": [{"department_id": "marketing", "key_aspects": {}}],
        "handoff_payload": {"ticket_id": "ticket-1", "workstreams": []},
    }
    with (
        patch("brasaland_api.modules.rfp_intake.router.run_rfp_intake", return_value=result),
        patch("brasaland_api.modules.rfp_intake.router.storage.persist_analysis") as persist,
        patch("brasaland_api.modules.rfp_intake.router.storage.persist_execution_events"),
        patch("brasaland_api.modules.rfp_intake.router.storage.update_ticket") as update,
        patch("brasaland_api.modules.rfp_intake.router.rfp_event_broker.publish") as publish_event,
    ):
        process_rfp_ticket("ticket-1", "/tmp/request.pdf", "rfp-1", "2026-10-22T14:32:00+00:00")

    persist.assert_called_once_with("ticket-1", result["metadata"], result["department_results"])
    publish_event.assert_called_once_with({
        "ticket_id": "ticket-1",
        "rfp_id": "rfp-1",
        "client_name": "Andes Tech Solutions",
        "location": None,
        "service_type": None,
        "status": "analyzing",
        "created_at": "2026-10-22T14:32:00+00:00",
    })
    assert update.call_args.args[0] == "ticket-1"
    assert update.call_args.args[1]["status"] == "analisis_completo"
    assert update.call_args.args[1]["handoff_payload"] == result["handoff_payload"]


def test_background_pipeline_marks_invalid_request_discarded():
    result = {"classification": {"is_valid": False, "reason": "No es RFP."}}
    with (
        patch("brasaland_api.modules.rfp_intake.router.run_rfp_intake", return_value=result),
        patch("brasaland_api.modules.rfp_intake.router.storage.persist_analysis") as persist,
        patch("brasaland_api.modules.rfp_intake.router.storage.persist_execution_events"),
        patch("brasaland_api.modules.rfp_intake.router.storage.update_ticket") as update,
        patch("brasaland_api.modules.rfp_intake.router.rfp_event_broker.publish") as publish_event,
    ):
        process_rfp_ticket("ticket-2", "/tmp/invalid.pdf")

    persist.assert_not_called()
    publish_event.assert_not_called()
    assert update.call_args.args[1]["status"] == "descartado"
    assert update.call_args.args[1]["processing_error"] == "No es RFP."


def test_background_failure_is_visible_without_falsely_completing_ticket():
    with (
        patch("brasaland_api.modules.rfp_intake.router.run_rfp_intake", side_effect=ValueError("bad pdf")),
        patch("brasaland_api.modules.rfp_intake.router.storage.update_ticket") as update,
    ):
        process_rfp_ticket("ticket-3", "/tmp/broken.pdf")

    values = update.call_args.args[1]
    assert "status" not in values
    assert values["processing_error"]