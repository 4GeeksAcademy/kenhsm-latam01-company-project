from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from data.pipelines.rag import generate_answer, retrieve


class AgentState(TypedDict):
    question: str
    context: list[dict[str, Any]]
    answer: str
    trace: list[dict[str, Any]]
    error: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_trace(state: AgentState, node: str, **payload: Any) -> None:
    state["trace"].append({"node": node, "timestamp": _utc_now_iso(), **payload})


def receive_question(state: AgentState) -> AgentState:
    question = (state.get("question") or "").strip()
    state["question"] = question
    state["context"] = state.get("context") or []
    state["answer"] = state.get("answer") or ""
    state["error"] = state.get("error")
    state["trace"] = state.get("trace") or []
    _append_trace(state, "receive_question", question=question, status="received")
    return state


def retrieve_context(state: AgentState) -> AgentState:
    question = (state.get("question") or "").strip()
    context = retrieve(question, k=5, min_score=0.35)
    state["context"] = context
    _append_trace(
        state,
        "retrieve_context",
        question=question,
        context_count=len(context),
        document_ids=[item.get("source_document") for item in context if item.get("source_document")],
    )
    return state


def respond_without_context(state: AgentState) -> AgentState:
    answer = (
        "No tengo información suficiente en la base de conocimiento de Brasaland para responder "
        "con precisión. Necesito más contexto sobre el tema solicitado antes de responder."
    )
    state["answer"] = answer
    state["error"] = "No hay contexto relevante"
    _append_trace(state, "respond_without_context", answer=answer)
    return state


def generate_response(state: AgentState) -> AgentState:
    question = (state.get("question") or "").strip()
    context = state.get("context") or []
    answer = generate_answer(question, context)
    state["answer"] = answer
    state["error"] = None
    _append_trace(
        state,
        "generate_answer",
        question=question,
        context_count=len(context),
        answer=answer,
    )
    return state


def route_after_question(state: AgentState) -> Literal["respond_without_context", "retrieve_context"]:
    if not (state.get("question") or "").strip():
        return "respond_without_context"
    return "retrieve_context"


def route_after_retrieve(state: AgentState) -> Literal["respond_without_context", "generate_answer"]:
    if not (state.get("context") or []):
        return "respond_without_context"
    return "generate_answer"


def build_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("respond_without_context", respond_without_context)
    builder.add_node("generate_answer", generate_response)

    builder.set_entry_point("receive_question")
    builder.add_conditional_edges(
        "receive_question",
        route_after_question,
        {
            "respond_without_context": "respond_without_context",
            "retrieve_context": "retrieve_context",
        },
    )
    builder.add_conditional_edges(
        "retrieve_context",
        route_after_retrieve,
        {
            "respond_without_context": "respond_without_context",
            "generate_answer": "generate_answer",
        },
    )
    builder.add_edge("respond_without_context", END)
    builder.add_edge("generate_answer", END)

    return builder.compile(checkpointer=MemorySaver())


def query_agent(question: str, *, thread_id: str | None = None) -> dict[str, Any]:
    if thread_id is None:
        thread_id = uuid.uuid4().hex

    graph = build_agent_graph()
    state = {
        "question": question or "",
        "context": [],
        "answer": "",
        "trace": [],
        "error": None,
    }
    result = graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
    if not result.get("answer"):
        result["answer"] = "No pude producir una respuesta fiable con el contexto disponible."
    return result
