"""Authenticated RFP intake ticket endpoints on the existing Brasaland API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.rfp_intake import storage
from brasaland_api.modules.rfp_intake.storage import RFPStorageError
from data.pipelines.rfp_intake.runner import run_rfp_intake

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rfp-intake", tags=["rfp-intake"], dependencies=[Depends(get_current_user)])
REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
RAW_RFP_DIRECTORY = REPOSITORY_ROOT / "data" / "raw" / "rfp-intake"
MAX_PDF_BYTES = 25 * 1024 * 1024


class RFPSubmissionAccepted(BaseModel):
    ticket_id: str
    status: str


def process_rfp_ticket(ticket_id: str, pdf_path: str) -> None:
    try:
        result = run_rfp_intake(ticket_id, pdf_path)
        classification = result.get("classification", {})
        if not classification.get("is_valid"):
            storage.update_ticket(ticket_id, {
                "status": "descartado",
                "processing_error": classification.get("reason", "Documento no clasificado como RFP accionable."),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        sections = result.get("department_results", [])
        storage.persist_analysis(ticket_id, result.get("metadata", {}), sections)
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

    background_tasks.add_task(process_rfp_ticket, ticket_id, str(pdf_path))
    return RFPSubmissionAccepted(ticket_id=ticket_id, status="analizando")


@router.get("")
def read_rfp_tickets(_current_user=Depends(get_current_user)) -> list[dict]:
    try:
        return storage.list_tickets()
    except RFPStorageError as error:
        raise HTTPException(status_code=503, detail="No se pudieron consultar los tickets.") from error


@router.get("/{ticket_id}")
def read_rfp_ticket(ticket_id: str, _current_user=Depends(get_current_user)) -> dict:
    try:
        ticket = storage.get_ticket(ticket_id)
    except RFPStorageError as error:
        raise HTTPException(status_code=503, detail="No se pudo consultar el ticket.") from error
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket RFP no encontrado.")
    return ticket