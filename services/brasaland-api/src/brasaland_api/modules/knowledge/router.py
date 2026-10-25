from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from data.pipelines.rag import query
from brasaland_api.core.rate_limit import agent_query_rate_limiter
from brasaland_api.core.deps import require_manager_or_admin
from brasaland_api.modules.agent.guardrails import sanitize_user_input

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=3000, description="Pregunta en lenguaje natural para la base de conocimiento")

    @field_validator("question", mode="before")
    @classmethod
    def sanitize_question(cls, value: object) -> str:
        return sanitize_user_input(value)


class KnowledgeQueryResponse(BaseModel):
    answer: str


@router.post(
    "/query",
    response_model=KnowledgeQueryResponse,
    dependencies=[Depends(require_manager_or_admin), Depends(agent_query_rate_limiter)],
)
def ask_knowledge(payload: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    answer = query(payload.question)
    return KnowledgeQueryResponse(answer=answer)
