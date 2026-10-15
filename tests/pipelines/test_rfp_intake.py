from data.pipelines.rfp_intake.graph import route_departments
from data.pipelines.rfp_intake.runtime import classify_rfp, rfp_intake_graph
from data.pipelines.rfp_intake.metrics_adapter import calculate_readability
from data.pipelines.rfp_intake.quality import annotate_handoff_questions
from data.pipelines.rfp_intake.workers import extract_relevant_excerpt, run_department_worker


def test_classifier_accepts_formal_and_informal_actionable_requests():
    formal = "Sunset Bay Resorts solicita una propuesta de concesión co-branded en 3 resorts de Florida por 12 meses."
    informal = "Andes Tech Solutions busca catering semanal para 220 empleados en Medellín, contrato de 12 meses, menú estándar."

    assert classify_rfp(formal)["is_valid"] is True
    assert classify_rfp(informal)["is_valid"] is True


def test_classifier_rejects_franchise_inquiry_without_actionable_scope():
    invalid = "Consulta de franquicia. Estamos interesados en conocer más."

    assert classify_rfp(invalid)["is_valid"] is False


def test_department_worker_only_returns_source_extracts_and_missing_fields():
    excerpt = "Catering semanal para 220 empleados en Medellín."
    result = run_department_worker({
        "department_id": "operaciones",
        "metadata": {"open_questions": ["deadline", "budget_range"]},
        "excerpt": excerpt,
    })

    assert result["contact"] == "Felipe Guerrero"
    assert result["key_aspects"]["source_extracts"] == [excerpt]
    assert result["key_aspects"]["open_questions"] == ["deadline"]


def test_department_routing_keeps_standard_menu_out_of_training():
    markdown = "Andes Tech solicita catering semanal para 220 empleados por 12 meses con menú estándar."

    assert route_departments(markdown) == ["marketing", "operaciones", "procurement"]


def test_graph_fans_out_and_synthesizes_handoff_for_four_departments():
    markdown = "Sunset Bay Resorts solicita concesión co-branded exclusiva en 3 resorts de Florida por 12 meses; incluye menú de autor y presupuesto de USD 60,000 anual."

    result = rfp_intake_graph.invoke({"ticket_id": "ticket-1", "markdown": markdown})

    assert result["classification"]["is_valid"] is True
    assert result["metadata"]["client_name"] == "Sunset Bay Resorts"
    assert result["departments_needed"] == ["marketing", "operaciones", "procurement", "training"]
    assert len(result["department_results"]) == 4
    assert result["handoff_payload"]["ticket_id"] == "ticket-1"


def test_readability_metrics_have_an_offline_fallback_for_long_documents():
    markdown = "This proposal describes recurring catering service and delivery requirements. " * 20

    metrics = calculate_readability(markdown)

    assert metrics["word_count"] > 100
    assert metrics["estimated_input_tokens"] > metrics["word_count"]
    assert metrics["flesch_kincaid_grade"] is not None
    assert metrics["gunning_fog"] is not None


def test_unknown_departments_and_conflicting_scope_are_escalated_not_routed():
    result = {
        "metadata": {"open_questions": []},
        "departments_needed": ["marketing", "operaciones"],
        "department_results": [{"department_id": "marketing", "key_aspects": {"open_questions": []}}],
        "handoff_payload": {"metadata": {}, "workstreams": []},
    }
    markdown = "La solicitud menciona el departamento de legal y requiere 220 empleados en una sección, pero 300 empleados en otra."

    annotate_handoff_questions(result, markdown)

    assert result["departments_needed"] == ["marketing", "operaciones"]
    assert any("legal" in question for question in result["metadata"]["open_questions"])
    assert any("220" in question and "300" in question for question in result["metadata"]["open_questions"])
    assert result["handoff_payload"]["metadata"] == result["metadata"]


def test_procurement_worker_gets_relevant_volume_and_only_its_open_questions():
    markdown = "Andes Tech solicita catering semanal para 220 empleados, menú estándar, contrato por 12 meses."
    excerpt = extract_relevant_excerpt(markdown, "procurement")
    result = run_department_worker({
        "department_id": "procurement",
        "metadata": {"open_questions": ["budget_range", "deadline", "client_name"]},
        "excerpt": excerpt,
    })

    assert "220 empleados" in result["key_aspects"]["source_extracts"][0]
    assert result["key_aspects"]["open_questions"] == ["budget_range", "deadline"]


def test_runner_converts_pdf_before_invoking_any_agent(monkeypatch):
    from types import SimpleNamespace

    from data.pipelines.rfp_intake import runner

    events = []
    result = {"classification": {"is_valid": False, "reason": "No es RFP."}}
    monkeypatch.setattr(runner, "convert_pdf_to_markdown", lambda path: events.append(("convert", path)) or "# Markdown")
    monkeypatch.setattr(
        runner,
        "rfp_intake_graph",
        SimpleNamespace(invoke=lambda state: events.append(("graph", state["markdown"])) or result),
    )

    assert runner.run_rfp_intake("ticket-4", "/tmp/request.pdf") == result
    assert events == [("convert", "/tmp/request.pdf"), ("graph", "# Markdown")]