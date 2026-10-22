"""Authenticated RFP intake ticket endpoints on the existing Brasaland API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.profiles import services as profile_services
from brasaland_api.modules.rfp_intake import storage
from brasaland_api.modules.rfp_intake.events import RFP_TICKET_CREATED, encode_sse_event, rfp_event_broker
from brasaland_api.modules.rfp_intake.approvals import initialize_approval_branches, respond_to_approval
from brasaland_api.modules.rfp_intake.storage import RFPStorageError
from brasaland_api.modules.rfp_intake.drafting import run_rfp_draft_generation
from data.pipelines.rfp_intake.runner import run_rfp_intake

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rfp-intake", tags=["rfp-intake"], dependencies=[Depends(get_current_user)])
REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
RAW_RFP_DIRECTORY = REPOSITORY_ROOT / "data" / "raw" / "rfp-intake"
MAX_PDF_BYTES = 25 * 1024 * 1024


class RFPSubmissionAccepted(BaseModel):
    ticket_id: str
    status: str


class RFPDraftGenerationAccepted(BaseModel):
    ticket_id: str
    status: str


class RFPApprovalRequest(BaseModel):
    action: Literal["approve", "reject", "request_changes"]
    comment: str | None = Field(default=None, max_length=2000)
    price_per_event_usd: float | None = Field(default=None, ge=0)
    cost_per_event_usd: float | None = Field(default=None, ge=0)
    setup_lead_time_business_days: int | None = Field(default=None, ge=0)


class RFPApprovalResponse(BaseModel):
    ticket_id: str
    status: str


class RFPFinalDocument(BaseModel):
    ticket_id: str
    document_markdown: str
    sections: list[dict[str, Any]]
    total_estimated_value: float | None = None
    currency: Literal["USD", "COP"]
    generated_at: datetime


def _execution_event(agent: str, input_value, output_value) -> dict:
    return {
        "event_id": str(uuid4()),
        "agent": agent,
        "input": input_value,
        "output": output_value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def process_rfp_ticket(ticket_id: str, pdf_path: str, rfp_id: str | None = None, created_at: str | None = None) -> None:
    try:
        result = run_rfp_intake(ticket_id, pdf_path)
        classification = result.get("classification", {})
        trace = [_execution_event("rfp_classifier", {"pdf_path": pdf_path}, classification)]
        if classification.get("is_valid"):
            trace.append(_execution_event("rfp_metadata_extractor", {"classification": classification}, result.get("metadata", {})))
            trace.extend(
                _execution_event(
                    f"department_worker:{section['department_id']}",
                    {"metadata": result.get("metadata", {}), "key_aspects": section.get("key_aspects", {})},
                    section,
                )
                for section in result.get("department_results", [])
            )
            trace.append(_execution_event("part_one_synthesizer", {"departments": result.get("metadata", {}).get("departments_needed", [])}, result.get("handoff_payload", {})))
        storage.persist_execution_events(ticket_id, trace)
        if not classification.get("is_valid"):
            storage.update_ticket(ticket_id, {
                "status": "descartado",
                "processing_error": classification.get("reason", "Documento no clasificado como RFP accionable."),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        sections = result.get("department_results", [])
        metadata = result.get("metadata", {})
        storage.persist_analysis(ticket_id, metadata, sections)
        if rfp_id and created_at:
            rfp_event_broker.publish({
                "ticket_id": ticket_id,
                "rfp_id": rfp_id,
                "client_name": metadata.get("client_name"),
                "location": metadata.get("location"),
                "service_type": metadata.get("service_type"),
                "status": "analyzing",
                "created_at": created_at,
            })
        storage.update_ticket(ticket_id, {
            "status": "analisis_completo",
            "processing_error": None,
            "handoff_payload": result.get("handoff_payload"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        logger.exception("RFP intake processing failed ticket_id=%s", ticket_id)
        try:
            storage.update_ticket(ticket_id, {
                "processing_error": "Error al convertir o analizar el documento. La recepción requiere reintento.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        except RFPStorageError:
            logger.exception("Could not record RFP processing failure ticket_id=%s", ticket_id)


def process_rfp_draft_ticket(ticket_id: str) -> None:
    try:
        ticket = storage.get_ticket(ticket_id)
        if ticket is None or ticket.get("status") != "generando_borrador":
            return

        def update_status(next_status: str) -> None:
            storage.update_ticket(ticket_id, {
                "status": next_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        def persist_progress(sections: list[dict], handoff_payload: dict) -> None:
            storage.persist_draft_sections(ticket_id, sections)
            storage.update_ticket(ticket_id, {
                "handoff_payload": handoff_payload,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            events = []
            for section in sections:
                department_id = section["department_id"]
                if section.get("draft_content"):
                    events.append(_execution_event(
                        f"department_generator:{department_id}",
                        {"key_aspects": section.get("key_aspects") or {}, "iteration_count": section.get("iteration_count")},
                        {"draft_content": section["draft_content"]},
                    ))
                if section.get("evaluation_results"):
                    events.append(_execution_event(
                        f"parallel_evaluators:{department_id}",
                        {"draft_content": section.get("draft_content")},
                        section["evaluation_results"],
                    ))
            storage.persist_execution_events(ticket_id, events)

        result = asyncio.run(run_rfp_draft_generation(
            ticket_id=ticket_id,
            metadata=ticket.get("metadata") or {},
            handoff_payload=ticket.get("handoff_payload") or {},
            department_sections=ticket.get("department_sections") or [],
            status_callback=update_status,
            progress_callback=persist_progress,
        ))
        storage.persist_execution_events(ticket_id, [
            _execution_event(
                "part_two_handoff",
                {"ticket_id": ticket_id},
                {"ticket_status": result.get("ticket_status"), "draft_generation": (result.get("handoff_payload") or {}).get("draft_generation", {})},
            )
        ])
        storage.update_ticket(ticket_id, {
            "status": result.get("ticket_status", "en_evaluación"),
            "handoff_payload": result.get("handoff_payload"),
            "processing_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        ticket = storage.get_ticket(ticket_id)
        if ticket is not None:
            initialize_approval_branches(ticket)
    except Exception:
        logger.exception("RFP draft generation failed ticket_id=%s", ticket_id)
        try:
            storage.update_ticket(ticket_id, {
                "processing_error": "No se pudo completar la generación/evaluación. El borrador requiere revisión o reintento.",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        except RFPStorageError:
            logger.exception("Could not record RFP draft failure ticket_id=%s", ticket_id)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=RFPSubmissionAccepted)
async def submit_rfp(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
) -> RFPSubmissionAccepted:
    filename = (file.filename or "").casefold()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Solo se aceptan archivos PDF.")

    content = await file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="El PDF supera el límite de 25 MB.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="El archivo no tiene una firma PDF válida.")

    ticket_id = str(uuid4())
    rfp_id = str(uuid4())
    RAW_RFP_DIRECTORY.mkdir(parents=True, exist_ok=True)
    pdf_path = RAW_RFP_DIRECTORY / f"{ticket_id}.pdf"
    pdf_path.write_bytes(content)
    now = datetime.now(timezone.utc).isoformat()
    try:
        storage.create_ticket({
            "ticket_id": ticket_id,
            "rfp_id": rfp_id,
            "status": "analizando",
            "raw_pdf_path": str(pdf_path.relative_to(REPOSITORY_ROOT)),
            "submitted_by": str(current_user.id),
            "created_at": now,
            "updated_at": now,
        })
    except RFPStorageError as error:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail="La recepción de RFP no está disponible.") from error

    background_tasks.add_task(process_rfp_ticket, ticket_id, str(pdf_path), rfp_id, now)
    return RFPSubmissionAccepted(ticket_id=ticket_id, status="analizando")


@router.get("")
def read_rfp_tickets(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    created_after: datetime | None = None,
    _current_user=Depends(get_current_user),
) -> list[dict]:
    try:
        return storage.list_tickets(limit=limit, offset=offset, created_after=created_after.isoformat() if created_after else None)
    except RFPStorageError as error:
        raise HTTPException(status_code=503, detail="No se pudieron consultar los tickets.") from error


@router.get("/events")
async def stream_rfp_events(request: Request) -> StreamingResponse:
    async def event_stream():
        subscriber = rfp_event_broker.subscribe()
        try:
            yield ": connected\n\n"
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(subscriber.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield encode_sse_event(RFP_TICKET_CREATED, event)
        finally:
            rfp_event_broker.unsubscribe(subscriber)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{ticket_id}", response_model=dict[str, Any])
def read_rfp_ticket(ticket_id: str, _current_user=Depends(get_current_user)) -> dict[str, Any]:
    try:
        ticket = storage.get_ticket(ticket_id)
    except RFPStorageError as error:
        raise HTTPException(status_code=503, detail="No se pudo consultar el ticket.") from error
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket RFP no encontrado.")
    return ticket


@router.get("/{ticket_id}/final-document", response_model=RFPFinalDocument)
def read_rfp_final_document(ticket_id: str, _current_user=Depends(get_current_user)) -> RFPFinalDocument:
    try:
        document = storage.get_final_document(ticket_id)
    except RFPStorageError as error:
        raise HTTPException(status_code=503, detail="No se pudo consultar el documento final.") from error
    if document is None:
        raise HTTPException(status_code=404, detail="El documento final aún no está disponible.")
    return RFPFinalDocument.model_validate(document)


@router.post("/{ticket_id}/approvals/{approval_key}", response_model=RFPApprovalResponse)
def submit_rfp_approval(
    ticket_id: str,
    approval_key: str,
    payload: RFPApprovalRequest,
    current_user=Depends(get_current_user),
) -> RFPApprovalResponse:
    profile = profile_services.get_profile_by_user_id(str(current_user.id))
    approver_name = profile.name if profile and profile.name else ""
    try:
        next_status = respond_to_approval(
            ticket_id,
            approval_key,
            approver_name,
            payload.model_dump(exclude_none=True),
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except RFPStorageError as error:
        raise HTTPException(status_code=503, detail="No se pudo guardar la aprobación RFP.") from error
    return RFPApprovalResponse(ticket_id=ticket_id, status=next_status)


@router.post("/{ticket_id}/generate-draft", status_code=status.HTTP_202_ACCEPTED, response_model=RFPDraftGenerationAccepted)
def generate_rfp_draft(
    ticket_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
) -> RFPDraftGenerationAccepted:
    try:
        ticket = storage.get_ticket(ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket RFP no encontrado.")
        if ticket.get("status") not in {"analisis_completo", "needs_human_review"}:
            raise HTTPException(status_code=409, detail="Solo se inicia generación desde análisis completo o revisión humana requerida.")
        if ticket.get("status") == "needs_human_review":
            profile = profile_services.get_profile_by_user_id(str(current_user.id))
            if not profile or (profile.name or "").strip().casefold() != "camila ospina":
                raise HTTPException(status_code=403, detail="Solo Camila Ospina puede reabrir una generación rechazada.")
        handoff = ticket.get("handoff_payload") or {}
        sections = ticket.get("department_sections") or []
        if handoff.get("ticket_id") != ticket_id or not sections:
            raise HTTPException(status_code=409, detail="El handoff de Parte 1 está incompleto.")
        if not storage.claim_draft_generation(ticket_id, expected_status=ticket["status"]):
            raise HTTPException(status_code=409, detail="El ticket ya no está disponible para generar un borrador.")
    except RFPStorageError as error:
        raise HTTPException(status_code=503, detail="No se pudo iniciar la generación del borrador.") from error

    background_tasks.add_task(process_rfp_draft_ticket, ticket_id)
    return RFPDraftGenerationAccepted(ticket_id=ticket_id, status="generando_borrador")