from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from brasaland_api.modules.incidents import services
from brasaland_api.modules.incidents.schemas import IncidentCreate, IncidentOut, IncidentStatusUpdate, IncidentSummary
from brasaland_shared.incidents import validate_incident_payload

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create(payload: IncidentCreate) -> IncidentOut:
    errors = validate_incident_payload(payload.model_dump())
    if errors:
        raise HTTPException(status_code=400, detail={"message": "Revisa los campos de la incidencia.", "fields": errors})
    return services.create_incident(payload.model_dump())


@router.get("/summary", response_model=IncidentSummary)
def get_summary() -> IncidentSummary:
    return services.summary()


@router.get("", response_model=list[IncidentOut])
def list_all(status_filter: str | None = Query(None, alias="status"), origin: str | None = None, branch: str | None = None, category: str | None = None) -> list[IncidentOut]:
    return services.list_incidents({"status": status_filter, "origin": origin, "branch": branch, "category": category})


@router.get("/{incident_id}", response_model=IncidentOut)
def get_one(incident_id: str) -> IncidentOut:
    record = services.get_incident(incident_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada.")
    return record


@router.patch("/{incident_id}/status", response_model=IncidentOut)
def change_status(incident_id: str, payload: IncidentStatusUpdate) -> IncidentOut:
    if payload.status not in ("open", "in_progress", "resolved", "discarded"):
        raise HTTPException(status_code=400, detail={"message": "Estado no permitido.", "fields": {"status": "El estado no está permitido."}})
    try:
        record = services.update_status(incident_id, payload.status)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"message": str(error), "fields": {"status": str(error)}}) from error
    if record is None:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada.")
    return record