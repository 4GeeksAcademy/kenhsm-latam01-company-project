from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from brasaland_api.core.deps import get_current_user
from brasaland_api.main import app
from brasaland_api.modules.rfp_intake import storage
from brasaland_api.modules.rfp_intake.router import process_rfp_ticket


def test_rfp_upload_requires_authentication():
    app.dependency_overrides.clear()
    client = TestClient(app)

    response = client.post("/rfp-intake", files={"file": ("request.pdf", b"%PDF-1.4", "application/pdf")})

    assert response.status_code == 401


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
    process_ticket.assert_called_once_with(ticket_id, str(raw_directory / f"{ticket_id}.pdf"))


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
        patch("brasaland_api.modules.rfp_intake.router.storage.update_ticket") as update,
    ):
        process_rfp_ticket("ticket-1", "/tmp/request.pdf")

    persist.assert_called_once_with("ticket-1", result["metadata"], result["department_results"])
    assert update.call_args.args[0] == "ticket-1"
    assert update.call_args.args[1]["status"] == "analisis_completo"
    assert update.call_args.args[1]["handoff_payload"] == result["handoff_payload"]


def test_background_pipeline_marks_invalid_request_discarded():
    result = {"classification": {"is_valid": False, "reason": "No es RFP."}}
    with (
        patch("brasaland_api.modules.rfp_intake.router.run_rfp_intake", return_value=result),
        patch("brasaland_api.modules.rfp_intake.router.storage.persist_analysis") as persist,
        patch("brasaland_api.modules.rfp_intake.router.storage.update_ticket") as update,
    ):
        process_rfp_ticket("ticket-2", "/tmp/invalid.pdf")

    persist.assert_not_called()
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