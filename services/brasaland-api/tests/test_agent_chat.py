from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from brasaland_api.core.rate_limit import FixedWindowRateLimiter
from brasaland_api.main import app
from brasaland_api.modules.agent import chat
from brasaland_api.modules.agent import graph as agent_graph


@pytest.fixture
def chat_client(tmp_path, monkeypatch):
    monkeypatch.setattr(chat, "store", chat.ChatSessionStore(tmp_path / "chat.sqlite3"))
    monkeypatch.setattr(chat, "runtime", chat.SessionRuntime())
    authenticated = []

    def resolve_user(token):
        authenticated.append(token)
        if token != "valid-test-token":
            raise ValueError("invalid token")
        return SimpleNamespace(id="manager-1")

    monkeypatch.setattr(chat, "get_current_user", resolve_user)
    return TestClient(app), authenticated


def test_websocket_rehydrates_and_streams_named_events(chat_client, monkeypatch):
    client, authenticated = chat_client

    async def fake_stream_agent(question, **kwargs):
        yield "custom", {"token": "Para "}
        yield "values", {"answer": "Para Brasaland"}

    monkeypatch.setattr(chat, "stream_agent", fake_stream_agent)
    with client.websocket_connect(
        "/agent/chat/chat-contract?token=valid-test-token&location_id=COL-01"
    ) as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["event"] == "session_snapshot"
        assert snapshot["data"]["agent_id"] == "manager_support"
        assert snapshot["data"]["location_id"] == "COL-01"
        assert snapshot["data"]["messages"] == []
        websocket.send_json({
            "event": "user_message",
            "data": {"session_id": "chat-contract", "text": "¿Qué debo revisar?"},
        })
        events = []
        while not any(event["event"] == "generation_completed" for event in events):
            events.append(websocket.receive_json())

    assert authenticated == ["valid-test-token"]
    assert [event["event"] for event in events] == [
        "user_message",
        "generation_started",
        "token_chunk",
        "token_chunk",
        "generation_completed",
    ]
    chunks = [event["data"] for event in events if event["event"] == "token_chunk"]
    assert [chunk["token"] for chunk in chunks] == ["Para ", "Brasaland"]
    assert [chunk["sequence"] for chunk in chunks] == [1, 2]
    assert len({event["data"]["event_sequence"] for event in events}) == len(events)


def test_interrupt_cancels_original_and_starts_new_turn(chat_client, monkeypatch):
    client, _ = chat_client

    async def fake_stream_agent(question, **kwargs):
        if question == "pregunta original":
            yield "custom", {"token": "parcial visible"}
            await asyncio.Event().wait()
        else:
            yield "custom", {"token": "redirección: "}
            yield "custom", {"token": question}
            yield "values", {"answer": f"redirección: {question}"}

    monkeypatch.setattr(chat, "stream_agent", fake_stream_agent)
    with client.websocket_connect(
        "/agent/chat/chat-interrupt?token=valid-test-token&location_id=FLA-01"
    ) as websocket:
        websocket.receive_json()
        websocket.send_json({
            "event": "user_message",
            "data": {"session_id": "chat-interrupt", "text": "pregunta original"},
        })
        first_token = websocket.receive_json()
        while first_token["event"] != "token_chunk":
            first_token = websocket.receive_json()
        original_message_id = first_token["data"]["message_id"]
        websocket.send_json({
            "event": "interrupt_requested",
            "data": {"session_id": "chat-interrupt", "new_input": "new_input Miami"},
        })
        events = []
        while not any(event["event"] == "generation_completed" for event in events):
            events.append(websocket.receive_json())

    event_names = [event["event"] for event in events]
    assert "generation_interrupted" in event_names
    assert event_names.index("generation_interrupted") < event_names.index("user_message")
    interrupted = next(event["data"] for event in events if event["event"] == "generation_interrupted")
    assert interrupted == {
        "message_id": original_message_id,
        "status": "interrupted",
        "session_id": "chat-interrupt",
        "event_sequence": interrupted["event_sequence"],
    }
    assert not any(
        event["event"] == "token_chunk" and event["data"]["message_id"] == original_message_id
        for event in events
    )
    new_turn_chunks = [
        event["data"]["token"]
        for event in events
        if event["event"] == "token_chunk" and event["data"]["message_id"] != original_message_id
    ]
    assert "new_input Miami" in "".join(new_turn_chunks)
    messages = chat.store.snapshot("chat-interrupt")["messages"]
    interrupted_message = next(message for message in messages if message["message_id"] == original_message_id)
    assert interrupted_message["text"] == "parcial visible"
    assert interrupted_message["status"] == "interrupted"
    assert messages[-1]["status"] == "completed"


def test_websocket_rejects_missing_jwt(chat_client):
    client, authenticated = chat_client
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/agent/chat/chat-no-auth?location_id=COL-01"):
            pass
    assert authenticated == []


def test_websocket_rejects_invalid_jwt(chat_client):
    client, authenticated = chat_client
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/agent/chat/chat-invalid-token?token=invalid&location_id=COL-01"
        ):
            pass
    assert authenticated == ["invalid"]


def test_websocket_sanitizes_input_and_rate_limits_model_turns(chat_client, monkeypatch):
    client, _ = chat_client
    questions = []

    async def fake_stream_agent(question, **kwargs):
        questions.append(question)
        yield "custom", {"token": "Respuesta segura."}
        yield "values", {"answer": "Respuesta segura."}

    monkeypatch.setattr(chat, "agent_query_rate_limiter", FixedWindowRateLimiter(max_requests=1))
    monkeypatch.setattr(chat, "stream_agent", fake_stream_agent)
    with client.websocket_connect(
        "/agent/chat/chat-rate-limit?token=valid-test-token&location_id=COL-01"
    ) as websocket:
        websocket.receive_json()
        websocket.send_json({
            "event": "user_message",
            "data": {"session_id": "chat-rate-limit", "text": "¿Qué revisar\x00 antes de abrir?"},
        })
        first_turn = []
        while not any(event["event"] == "generation_completed" for event in first_turn):
            first_turn.append(websocket.receive_json())

        websocket.send_json({
            "event": "user_message",
            "data": {"session_id": "chat-rate-limit", "text": "Otra consulta"},
        })
        limited = websocket.receive_json()

    assert questions == ["¿Qué revisar antes de abrir?"]
    assert limited["event"] == "chat_error"
    assert "Límite de consultas" in limited["data"]["detail"]


def test_session_event_bus_fans_out_without_duplicate_producers():
    async def verify_fanout():
        bus = chat.SessionEventBus()
        first = bus.subscribe("chat-fanout")
        second = bus.subscribe("chat-fanout")
        event = {"event": "token_chunk", "data": {"token": "uno"}}
        await bus.publish("chat-fanout", event)
        assert await first.get() == event
        assert await second.get() == event

    asyncio.run(verify_fanout())


def test_chat_session_is_bound_to_owner_and_location(tmp_path):
    store = chat.ChatSessionStore(tmp_path / "owner.sqlite3")
    store.open_session("chat-owner", "manager-1", "COL-01")
    with pytest.raises(PermissionError):
        store.open_session("chat-owner", "manager-2", "COL-01")
    with pytest.raises(ValueError):
        store.open_session("chat-owner", "manager-1", "FLA-01")


def test_cancelling_generation_closes_async_model_stream(monkeypatch):
    class FakeStream:
        def __init__(self):
            self.closed = False
            self.wait_for_cancel = asyncio.Event()

        async def __aiter__(self):
            yield SimpleNamespace(
                choices=[SimpleNamespace(delta=SimpleNamespace(content='{"answer":"partial'))]
            )
            await self.wait_for_cancel.wait()

        async def close(self):
            self.closed = True

    class FakeCompletions:
        def __init__(self, stream):
            self.stream = stream

        async def create(self, **kwargs):
            return self.stream

    class FakeClient:
        def __init__(self, stream):
            self.chat = SimpleNamespace(completions=FakeCompletions(stream))
            self.closed = False

        async def close(self):
            self.closed = True

    async def verify_cancel():
        stream = FakeStream()
        client = FakeClient(stream)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.delenv("FOURGEEKS_API_KEY", raising=False)
        monkeypatch.setattr(agent_graph, "AsyncOpenAI", lambda **kwargs: client)
        first_token = asyncio.Event()
        tokens = []

        def write(event):
            tokens.append(event["token"])
            first_token.set()

        task = asyncio.create_task(
            agent_graph._generate_structured_response_stream(
                "pregunta",
                [],
                [],
                [],
                session_id="chat-cancel",
                writer=write,
            )
        )
        await asyncio.wait_for(first_token.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert tokens == ["partial"]
        assert stream.closed is True
        assert client.closed is True

    asyncio.run(verify_cancel())