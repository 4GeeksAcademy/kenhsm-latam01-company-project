from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from data.pipelines.rag import query

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pregunta en lenguaje natural para la base de conocimiento")


class KnowledgeQueryResponse(BaseModel):
    answer: str


@router.post("/query", response_model=KnowledgeQueryResponse)
def ask_knowledge(payload: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    answer = query(payload.question)
    return KnowledgeQueryResponse(answer=answer)
