from __future__ import annotations

import uuid
import json
import os
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from data.pipelines.rag import generate_answer, retrieve


class AgentState(TypedDict):
    question: str
    tool_action: str | None
    tool_arguments: dict[str, Any]
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
    state["tool_action"] = state.get("tool_action")
    state["tool_arguments"] = state.get("tool_arguments") or {}
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


async def run_mcp_tool(state: AgentState) -> AgentState:
    action = state.get("tool_action") or ""
    tool_result = None
    error_code = None
    try:
        access_token = os.getenv("BRASALAND_MCP_ACCESS_TOKEN", "")
        if not access_token:
            raise RuntimeError("MCP_ACCESS_TOKEN_MISSING")
        client = MultiServerMCPClient({
            "brasaland": {
                "transport": "streamable_http",
                "url": os.getenv("BRASALAND_MCP_URL", "http://127.0.0.1:8787/mcp"),
                "headers": {"Authorization": f"Bearer {access_token}"},
            }
        }, handle_tool_errors=False)
        tools = await client.get_tools(server_name="brasaland")
        selected_tool = next((tool for tool in tools if tool.name == action), None)
        if selected_tool is None:
            raise ValueError("MCP_TOOL_NOT_FOUND")
        tool_result = await selected_tool.ainvoke(state.get("tool_arguments") or {})
        answer = tool_result if isinstance(tool_result, str) else json.dumps(tool_result, ensure_ascii=False, default=str)
        state["answer"] = answer
        state["error"] = None
    except Exception as error:
        error_code = str(error).split(":", 1)[0] or "MCP_TOOL_ERROR"
        state["answer"] = "No se pudo completar la acción solicitada a través del servidor MCP."
        state["error"] = error_code
    _append_trace(
        state,
        "mcp_tool",
        tool=action,
        result="error" if error_code else "success",
        error_code=error_code,
        output=tool_result if error_code is None else None,
    )
    return state


def route_after_question(state: AgentState) -> Literal["respond_without_context", "retrieve_context", "run_mcp_tool"]:
    if state.get("tool_action"):
        return "run_mcp_tool"
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
    builder.add_node("run_mcp_tool", run_mcp_tool)

    builder.set_entry_point("receive_question")
    builder.add_conditional_edges(
        "receive_question",
        route_after_question,
        {
            "run_mcp_tool": "run_mcp_tool",
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
    builder.add_edge("run_mcp_tool", END)

    return builder.compile(checkpointer=MemorySaver())


async def query_agent(
    question: str,
    *,
    thread_id: str | None = None,
    tool_action: str | None = None,
    tool_arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if thread_id is None:
        thread_id = uuid.uuid4().hex

    graph = build_agent_graph()
    state = {
        "question": question or "",
        "tool_action": tool_action,
        "tool_arguments": tool_arguments or {},
        "context": [],
        "answer": "",
        "trace": [],
        "error": None,
    }
    result = await graph.ainvoke(state, config={"configurable": {"thread_id": thread_id}})
    if not result.get("answer"):
        result["answer"] = "No pude producir una respuesta fiable con el contexto disponible."
    return result
