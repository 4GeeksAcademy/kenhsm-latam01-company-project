from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from brasaland_api.modules.agent.graph import query_agent

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pregunta en lenguaje natural para la base de conocimiento")


class AgentQueryResponse(BaseModel):
    answer: str
    trace: list[dict[str, Any]] = []


@router.post("/query", response_model=AgentQueryResponse)
def ask_agent(payload: AgentQueryRequest) -> AgentQueryResponse:
    try:
        result = query_agent(payload.question)
        return AgentQueryResponse(answer=result.get("answer", ""), trace=result.get("trace", []))
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"detail": "El agente no pudo procesar la solicitud. Inténtalo de nuevo más tarde."},
        )
