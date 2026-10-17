from __future__ import annotations

from pydantic import BaseModel, Field

from brasaland_api.modules.incidents import services
from brasaland_api.modules.incidents.schemas import IncidentOut


class IncidentLookupInput(BaseModel):
    incident_id: str = Field(min_length=1, max_length=100)


class IncidentLookupOutput(BaseModel):
    found: bool
    incident: IncidentOut | None = None


def lookup_incident(payload: IncidentLookupInput) -> IncidentLookupOutput:
    """Read an incident by API id or its imported source key."""
    identifier = payload.incident_id.strip()
    incident = services.get_incident(identifier) or services.find_source_key(identifier)
    if incident is None:
        return IncidentLookupOutput(found=False)
    return IncidentLookupOutput(found=True, incident=IncidentOut.model_validate(incident))