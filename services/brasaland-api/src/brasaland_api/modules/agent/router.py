from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from brasaland_api.modules.agent.graph import query_agent
from brasaland_api.modules.agent.memory import AgentMemoryStore
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
    memory_proposal: dict[str, Any] | None = None
    memory_decision: dict[str, Any] | None = None


@router.get("/memory")
def read_agent_memory(current_user=Depends(get_current_user)) -> list[dict[str, Any]]:
    return AgentMemoryStore().read_memories(current_user.id)


@router.get("/memory/audit")
def read_agent_memory_audit(current_user=Depends(get_current_user)) -> list[dict[str, Any]]:
    return AgentMemoryStore().audit_log(current_user.id)


@router.post("/query", response_model=AgentQueryResponse)
async def ask_agent(
    payload: AgentQueryRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
) -> AgentQueryResponse:
    actor_id = None
    if payload.tool_action:
        if credentials is None:
            raise HTTPException(
                status_code=401,
                detail="Se requiere autenticación para ejecutar herramientas del agente.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    if credentials is not None:
        actor_id = get_current_user(credentials.credentials).id
    try:
        result = await query_agent(
            payload.question,
            actor_id=actor_id,
            tool_action=payload.tool_action,
            tool_arguments=payload.tool_arguments,
        )
        return AgentQueryResponse(
            answer=result.get("answer", ""),
            trace=result.get("trace", []),
            error=result.get("error"),
            memory_proposal=result.get("memory_proposal"),
            memory_decision=result.get("memory_decision"),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"detail": "El agente no pudo procesar la solicitud. Inténtalo de nuevo más tarde."},
        )
