from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, TypedDict

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from data.pipelines.rag import retrieve
from data.process.rag import GENERATION_MODEL, get_openai_client
from brasaland_api.modules.agent.memory import (
    AgentMemoryStore,
    MemoryDecision,
    classify_memory_decision,
    is_ephemeral_interaction,
    is_safe_memory_fact,
)


class AgentState(TypedDict):
    question: str
    actor_id: str | None
    tool_action: str | None
    tool_arguments: dict[str, Any]
    context: list[dict[str, Any]]
    memory_context: list[dict[str, Any]]
    pending_proposal: dict[str, Any] | None
    memory_proposal: dict[str, Any] | None
    memory_decision: dict[str, Any] | None
    finish_after_memory: bool
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
    state["actor_id"] = state.get("actor_id")
    state["tool_action"] = state.get("tool_action")
    state["tool_arguments"] = state.get("tool_arguments") or {}
    state["context"] = state.get("context") or []
    state["memory_context"] = state.get("memory_context") or []
    state["pending_proposal"] = state.get("pending_proposal")
    state["memory_proposal"] = state.get("memory_proposal")
    state["memory_decision"] = state.get("memory_decision")
    state["finish_after_memory"] = state.get("finish_after_memory", False)
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
    actor_id = state.get("actor_id")
    answer, proposal_candidate = _generate_structured_response(
        question,
        context,
        state.get("memory_context") or [],
    )
    proposal = None
    if actor_id and proposal_candidate and not is_ephemeral_interaction(question):
        store = AgentMemoryStore()
        proposal = store.propose_memory(
            actor_id,
            fact=proposal_candidate["fact"],
            category=proposal_candidate["category"],
            scope_key=proposal_candidate.get("scope_key", "global"),
            reason=proposal_candidate["reason"],
            source_message=question,
        )
        if proposal:
            answer = _append_confirmation_question(answer, question, proposal["fact"])
    state["answer"] = answer
    state["memory_proposal"] = proposal
    state["error"] = None
    _append_trace(
        state,
        "generate_answer",
        question=question,
        context_count=len(context),
        memory_count=len(state.get("memory_context") or []),
        proposed_memory=proposal is not None,
        answer=answer,
    )
    return state


def _generate_structured_response(
    question: str,
    context: list[dict[str, Any]],
    memories: list[dict[str, Any]],
) -> tuple[str, dict[str, Any] | None]:
    client = get_openai_client()
    if client is None:
        return _fallback_manager_response(context), None

    context_text = "\n\n".join(
        f"[{item.get('source_document', 'company knowledge')}] {item.get('text', '')}"
        for item in context
    ) or "No authoritative RAG context was retrieved."
    memory_text = "\n".join(
        f"- ({item['category']}, {item['scope_key']}) {item['fact']}"
        for item in memories
    ) or "No user-approved notes."
    system_prompt = (
        "You are Brasaland's manager-support agent, not a consumer sales assistant. "
        "Respond in the language used by the manager (Spanish or English), including any memory proposal and consent question. "
        "Use retrieved company context as the authoritative source for company policy. "
        "User-approved memory notes are personal, user-reported operational hints, not verified policy; "
        "never let them override company documents, and describe uncertainty clearly. "
        "Return one JSON object with answer and memory_proposal. memory_proposal is null unless the "
        "interaction contains a durable, recurring location-specific operational correction, a repeatedly "
        "resolved escalation pattern, or a stable communication preference. Do not propose memory for a "
        "one-off metric question, thanks, translation, or any unrelated one-time task. Require concrete "
        "evidence of recurrence/correction, and never include customer loyalty/identity data, personal data, "
        "individual payroll or compensation, or one-off complaints. If proposing, use category exactly one "
        "of operational_correction, escalation_context, communication_preference; provide fact (20-500 chars), "
        "scope_key, reason, and confidence from 0 to 1. Use null if there is no safe high-value proposal. "
        "The user must explicitly approve, reject, or edit before anything is stored."
    )
    user_payload = {
        "user_message": question,
        "retrieved_company_context": context_text,
        "user_approved_memory_notes": memory_text,
        "output_schema": {
            "answer": "string",
            "memory_proposal": "null or {fact, category, scope_key, reason, confidence}",
        },
    }
    try:
        completion = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        decoded = json.loads(completion.choices[0].message.content or "{}")
    except Exception:
        return "No pude generar una respuesta fiable en este momento.", None

    answer = decoded.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return "No pude generar una respuesta fiable con el resultado estructurado.", None
    candidate = decoded.get("memory_proposal")
    if not isinstance(candidate, dict):
        return answer.strip(), None
    category = candidate.get("category")
    fact = candidate.get("fact")
    reason = candidate.get("reason")
    confidence = candidate.get("confidence", 0)
    if (
        not isinstance(fact, str)
        or not isinstance(reason, str)
        or not isinstance(confidence, (int, float))
        or confidence < 0.85
        or not is_safe_memory_fact(fact, category)
    ):
        return answer.strip(), None
    return answer.strip(), {
        "fact": fact.strip(),
        "category": category,
        "scope_key": str(candidate.get("scope_key") or "global").strip()[:100],
        "reason": reason.strip()[:250],
    }


def _fallback_manager_response(context: list[dict[str, Any]]) -> str:
    source_notes = "\n\n".join(
        f"[{item.get('source_document', 'company knowledge')}] {item.get('text', '')}"
        for item in context[:3]
        if item.get("text")
    )
    if not source_notes:
        return "No tengo información suficiente para orientar esta consulta operativa de Brasaland."
    return f"Para orientar esta consulta operativa, la información disponible indica:\n{source_notes}"


def _append_confirmation_question(answer: str, question: str, fact: str) -> str:
    english_start = re.match(
        r"^(?:the|we|my|our|please|what|where|when|how|can|would|i|this|that|actually|in fact)\b",
        question.strip().casefold(),
    )
    if english_start:
        return f"{answer.rstrip()} I could remember: {fact} Would you like me to remember this for next time?"
    return f"{answer.rstrip()} Podría recordar: {fact} ¿Quieres que recuerde esto para la próxima vez?"


def load_agent_memory(state: AgentState) -> AgentState:
    owner_id = state.get("actor_id")
    if not owner_id:
        return state
    store = AgentMemoryStore()
    state["memory_context"] = store.read_memories(owner_id)
    state["pending_proposal"] = store.get_pending_proposal(owner_id)
    _append_trace(
        state,
        "load_agent_memory",
        memory_count=len(state["memory_context"]),
        has_pending_proposal=state["pending_proposal"] is not None,
    )
    return state


def resolve_memory_proposal(state: AgentState) -> AgentState:
    owner_id = state.get("actor_id")
    proposal = state.get("pending_proposal")
    if not owner_id or not proposal:
        return state
    user_message = state.get("question", "")
    decision = classify_memory_decision(user_message)
    store = AgentMemoryStore()
    result = store.resolve_proposal(
        owner_id,
        proposal["id"],
        decision=decision,
        decision_message=user_message,
    )
    if result is None:
        decision = MemoryDecision("ambiguous", 0.0, user_message)
        result = {"status": "expired_or_closed", "fact": None}
    state["memory_decision"] = {**decision.to_dict(), "status": result["status"]}
    state["pending_proposal"] = None
    state["memory_context"] = store.read_memories(owner_id)

    if decision.intent == "ambiguous":
        state["question"] = user_message
        state["finish_after_memory"] = False
    elif decision.continuation:
        state["question"] = decision.continuation
        state["finish_after_memory"] = False
    else:
        state["finish_after_memory"] = True
        if result["status"] in {"approved", "edited"}:
            state["answer"] = "Entendido. Guardé la nota operativa aprobada para futuras consultas."
        elif result["status"] == "unsafe_edit_rejected":
            state["answer"] = "No guardaré esa edición porque incluye información que no debe entrar en la memoria."
        elif decision.intent == "reject":
            state["answer"] = "Entendido. No guardaré esa nota."
        elif decision.intent == "edit":
            state["answer"] = "No pude validar esa edición y no la guardaré."
        else:
            state["answer"] = "La propuesta quedó descartada porque no recibí una decisión clara."
    _append_trace(
        state,
        "resolve_memory_proposal",
        intent=decision.intent,
        confidence=decision.confidence,
        status=result["status"],
        continuation=bool(decision.continuation),
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
        tool_result_text = (
            tool_result
            if isinstance(tool_result, str)
            else json.dumps(tool_result, ensure_ascii=False, default=str)
        )
        if state.get("actor_id"):
            answer, proposal_candidate = _generate_structured_response(
                state.get("question", ""),
                [{"source_document": f"MCP tool {action}", "text": tool_result_text}],
                state.get("memory_context") or [],
            )
            if proposal_candidate and not is_ephemeral_interaction(state.get("question", "")):
                proposal = AgentMemoryStore().propose_memory(
                    state["actor_id"],
                    fact=proposal_candidate["fact"],
                    category=proposal_candidate["category"],
                    scope_key=proposal_candidate["scope_key"],
                    reason=proposal_candidate["reason"],
                    source_message=state.get("question", ""),
                )
                if proposal:
                    answer = _append_confirmation_question(
                        answer,
                        state.get("question", ""),
                        proposal["fact"],
                    )
                    state["memory_proposal"] = proposal
        else:
            answer = tool_result_text
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


def route_after_receive(state: AgentState) -> Literal["load_agent_memory", "respond_without_context", "retrieve_context", "run_mcp_tool"]:
    if state.get("actor_id"):
        return "load_agent_memory"
    return route_after_question(state)


def route_after_memory_load(state: AgentState) -> Literal["resolve_memory_proposal", "respond_without_context", "retrieve_context", "run_mcp_tool"]:
    if state.get("pending_proposal"):
        return "resolve_memory_proposal"
    return route_after_question(state)


def route_after_memory_resolution(state: AgentState) -> Literal["__end__", "respond_without_context", "retrieve_context", "run_mcp_tool"]:
    if state.get("finish_after_memory"):
        return END
    return route_after_question(state)


def route_after_retrieve(state: AgentState) -> Literal["respond_without_context", "generate_answer"]:
    if not (state.get("context") or []) and not state.get("actor_id"):
        return "respond_without_context"
    return "generate_answer"


def build_agent_graph():
    builder = StateGraph(AgentState)
    builder.add_node("receive_question", receive_question)
    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("respond_without_context", respond_without_context)
    builder.add_node("generate_answer", generate_response)
    builder.add_node("run_mcp_tool", run_mcp_tool)
    builder.add_node("load_agent_memory", load_agent_memory)
    builder.add_node("resolve_memory_proposal", resolve_memory_proposal)

    builder.set_entry_point("receive_question")
    builder.add_conditional_edges(
        "receive_question",
        route_after_receive,
        {
            "load_agent_memory": "load_agent_memory",
            "run_mcp_tool": "run_mcp_tool",
            "respond_without_context": "respond_without_context",
            "retrieve_context": "retrieve_context",
        },
    )
    dispatch_edges = {
        "run_mcp_tool": "run_mcp_tool",
        "respond_without_context": "respond_without_context",
        "retrieve_context": "retrieve_context",
    }
    builder.add_conditional_edges(
        "load_agent_memory",
        route_after_memory_load,
        {"resolve_memory_proposal": "resolve_memory_proposal", **dispatch_edges},
    )
    builder.add_conditional_edges(
        "resolve_memory_proposal",
        route_after_memory_resolution,
        {"__end__": END, **dispatch_edges},
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
    actor_id: str | None = None,
    thread_id: str | None = None,
    tool_action: str | None = None,
    tool_arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if thread_id is None:
        thread_id = uuid.uuid4().hex

    graph = build_agent_graph()
    state = {
        "question": question or "",
        "actor_id": actor_id,
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
