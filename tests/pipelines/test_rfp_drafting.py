from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SERVICE_SRC = Path(__file__).resolve().parents[2] / "services" / "brasaland-api" / "src"
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from brasaland_api.modules.rfp_intake import drafting as drafting_runtime
from data.pipelines.rfp_intake.drafting import (
    evaluate_compliance,
    generate_department_draft,
    MAX_DRAFT_ITERATIONS,
)
from data.pipelines.rfp_intake import drafting
from data.pipelines.rfp_intake.drafting_adapter import run_rfp_draft_generation


def test_department_generator_uses_handoff_inputs_without_raw_pdf(monkeypatch):
    _ = drafting_runtime
    monkeypatch.setattr("data.pipelines.rfp_intake.drafting.get_openai_client", lambda: None)
    metadata = {
        "client_name": "Andes Tech Solutions",
        "location": "Medellín",
        "service_type": "catering semanal",
        "scope": ["Catering semanal para 220 empleados durante 12 meses."],
        "open_questions": ["budget_range"],
    }
    aspects = {
        "department_name": "Operaciones de Restaurante",
        "focus": "capacidad, personal, montaje y costo operativo por evento",
        "source_extracts": ["Catering semanal para 220 empleados en Medellín."],
        "open_questions": ["budget_range"],
    }

    draft = generate_department_draft("operaciones", metadata, aspects)

    assert "Operaciones de Restaurante" in draft
    assert "220 empleados" in draft
    assert "budget_range" in draft
    assert "10 días hábiles" in draft
    assert "PDF" not in draft

    department_terms = {
        "marketing": "co-branding",
        "operaciones": "capacidad",
        "procurement": "proveedores",
        "training": "certificación",
    }
    for department_id, term in department_terms.items():
        section_draft = generate_department_draft(department_id, metadata, aspects)
        assert term in section_draft.casefold()


def test_compliance_evaluator_rejects_setup_promise_below_ten_business_days():
    draft = (
        "Calidad consistente, experiencia cálida y velocidad de servicio. "
        "La oferta tiene validez de 30 días desde su emisión. "
        "Prometemos montaje en 5 días hábiles."
    )

    result = evaluate_compliance(draft, {})

    assert result["pass"] is False
    assert "No prometer montaje ni entrega en menos de 10 días hábiles." in result["violations"]


def test_compliance_evaluator_requires_dual_currency_and_rejects_competitor_names():
    draft = (
        "Calidad consistente, experiencia cálida y velocidad de servicio. "
        "La oferta tiene validez de 30 días desde su emisión. "
        "El precio anual es USD 60,000 y debe compararse con Burger King. "
        "Montaje y entrega requieren al menos 10 días hábiles."
    )

    result = evaluate_compliance(draft, {})

    assert result["pass"] is False
    assert any("COP como en USD" in violation for violation in result["violations"])
    assert any("burger king" in violation.casefold() for violation in result["violations"])


def _part_one_payload():
    metadata = {
        "client_name": "Andes Tech Solutions",
        "location": "Medellín",
        "service_type": "catering semanal",
        "scope": ["Catering semanal para 220 empleados durante 12 meses."],
        "budget_range": "USD 60,000-75,000 per year",
        "open_questions": ["budget_range"],
    }
    aspects = {
        "department_name": "Operaciones de Restaurante",
        "contact": "Felipe Guerrero",
        "focus": "capacidad, personal, montaje y costo operativo por evento",
        "source_extracts": ["Catering semanal para 220 empleados en Medellín."],
        "open_questions": ["budget_range"],
    }
    handoff = {
        "ticket_id": "ticket-draft-1",
        "departments_needed": ["operaciones"],
        "metadata": metadata,
        "workstreams": [{"department_id": "operaciones", "key_aspects": aspects}],
    }
    sections = [{"ticket_id": "ticket-draft-1", "department_id": "operaciones", "key_aspects": aspects}]
    return metadata, handoff, sections


def test_drafting_graph_consumes_handoff_and_emits_structured_part_three_sections(monkeypatch):
    monkeypatch.setattr("data.pipelines.rfp_intake.drafting.get_openai_client", lambda: None)
    metadata, handoff, sections = _part_one_payload()
    statuses = []
    progress = []

    result = asyncio.run(run_rfp_draft_generation(
        ticket_id="ticket-draft-1",
        metadata=metadata,
        handoff_payload=handoff,
        department_sections=sections,
        status_callback=statuses.append,
        progress_callback=lambda saved_sections, saved_handoff: progress.append((saved_sections, saved_handoff)),
    ))

    section = result["sections"]["operaciones"]
    evaluation = section["evaluation_results"]
    assert section["iteration_count"] == 1
    assert evaluation["overall_pass"] is True
    assert set(evaluation) >= {"readability", "relevance", "compliance", "feedback_for_generator"}
    assert result["handoff_payload"]["draft_generation"]["status"] == "ready_for_part_3"
    assert result["handoff_payload"]["required_approvals"] == ["Mariana Restrepo"]
    assert result["handoff_payload"]["workstreams"][0]["draft_content"] == section["draft_content"]
    assert statuses == ["generando_borrador", "en_evaluación"]
    assert len(progress) == 2


def test_failed_evaluation_returns_feedback_to_department_generator(monkeypatch):
    metadata, handoff, sections = _part_one_payload()
    generated = []
    monkeypatch.setattr("data.pipelines.rfp_intake.drafting.get_openai_client", lambda: None)

    def generator(department_id, department_metadata, key_aspects, *, previous_draft="", feedback=""):
        generated.append({"previous_draft": previous_draft, "feedback": feedback})
        if len(generated) == 1:
            return "Prometemos montaje en 5 días hábiles."
        return (
            "Operaciones revisará capacidad y personal para catering semanal a 220 empleados en Medellín durante 12 meses. "
            "Se consideran montaje y costo operativo por evento; budget_range (presupuesto pendiente). "
            "El borrador conserva calidad consistente, experiencia cálida y velocidad de servicio. "
            "La oferta tendrá validez de 30 días desde emisión. "
            "Montaje y entrega requieren un mínimo de 10 días hábiles. "
            "El precio se confirmará en COP y USD con tipo de cambio aprobado. "
            "Felipe Guerrero revisará capacidad y costo antes de cotizar."
        )

    monkeypatch.setattr(drafting, "generate_department_draft", generator)
    result = asyncio.run(run_rfp_draft_generation(
        ticket_id="ticket-draft-1",
        metadata=metadata,
        handoff_payload=handoff,
        department_sections=sections,
    ))

    assert len(generated) == 2
    assert "10 días hábiles" in generated[1]["feedback"]
    assert generated[1]["previous_draft"] == "Prometemos montaje en 5 días hábiles."
    assert result["sections"]["operaciones"]["evaluation_results"]["overall_pass"] is True


def test_exhausted_evaluation_keeps_last_draft_and_marks_human_review(monkeypatch):
    metadata, handoff, sections = _part_one_payload()
    monkeypatch.setattr("data.pipelines.rfp_intake.drafting.generate_department_draft", lambda *args, **kwargs: "Prometemos montaje en 5 días hábiles.")
    statuses = []

    result = asyncio.run(run_rfp_draft_generation(
        ticket_id="ticket-draft-1",
        metadata=metadata,
        handoff_payload=handoff,
        department_sections=sections,
        status_callback=statuses.append,
    ))

    section = result["sections"]["operaciones"]
    assert section["iteration_count"] == MAX_DRAFT_ITERATIONS
    assert section["draft_content"] == "Prometemos montaje en 5 días hábiles."
    assert section["section_status"] == "needs_human_review"
    assert section["evaluation_results"]["overall_pass"] is False
    assert result["ticket_status"] == "needs_human_review"
    assert result["handoff_payload"]["draft_generation"]["sections"][0]["evaluation_results"]
    assert statuses[-1] == "needs_human_review"