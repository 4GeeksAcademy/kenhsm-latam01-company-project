from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from brasaland_api.modules.agent.graph import query_agent
from brasaland_api.core.deps import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])
optional_bearer = HTTPBearer(auto_error=False)


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pregunta en lenguaje natural para la base de conocimiento")
    tool_action: Literal[
        "create_incident",
        "get_incident",
        "update_incident_status",
        "list_inventory",
        "write_inventory",
    ] | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)


class AgentQueryResponse(BaseModel):
    answer: str
    trace: list[dict[str, Any]] = []
    error: str | None = None


@router.post("/query", response_model=AgentQueryResponse)
async def ask_agent(
    payload: AgentQueryRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
) -> AgentQueryResponse:
    if payload.tool_action:
        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail="Se requiere autenticación para ejecutar herramientas del agente.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        get_current_user(credentials.credentials)
    try:
        result = await query_agent(
            payload.question,
            tool_action=payload.tool_action,
            tool_arguments=payload.tool_arguments,
        )
        return AgentQueryResponse(
            answer=result.get("answer", ""),
            trace=result.get("trace", []),
            error=result.get("error"),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"detail": "El agente no pudo procesar la solicitud. Inténtalo de nuevo más tarde."},
        )
