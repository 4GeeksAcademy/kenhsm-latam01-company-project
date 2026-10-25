from __future__ import annotations

import asyncio
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from brasaland_api.core.rate_limit import agent_query_rate_limiter
from brasaland_api.core.deps import get_current_user
from brasaland_api.modules.agent.guardrails import sanitize_user_input
from brasaland_api.modules.agent.graph import stream_agent

router = APIRouter(tags=["manager support chat"])
LOCATION_IDS = {
    *(f"COL-{number:02d}" for number in range(1, 11)),
    *(f"FLA-{number:02d}" for number in range(1, 5)),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatSessionStore:
    def __init__(self, path: str | Path | None = None):
        if path is None:
            default_path = Path.home() / ".local" / "state" / "brasaland" / "chat_sessions.sqlite3"
            path = os.getenv("CHAT_SESSION_DB_PATH", str(default_path))
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL CHECK (agent_id = 'manager_support'),
                    user_id TEXT NOT NULL,
                    location_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('active', 'interrupted', 'closed')),
                    created_at TEXT NOT NULL,
                    event_sequence INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES chat_sessions(session_id),
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS chat_messages_session_created
                    ON chat_messages(session_id, created_at, message_id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def open_session(self, session_id: str, user_id: str, location_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None:
                created_at = _now()
                connection.execute(
                    "INSERT INTO chat_sessions(session_id, agent_id, user_id, location_id, status, created_at) "
                    "VALUES (?, 'manager_support', ?, ?, 'active', ?)",
                    (session_id, user_id, location_id, created_at),
                )
                row = connection.execute(
                    "SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
            elif row["user_id"] != user_id:
                raise PermissionError("La sesión pertenece a otro usuario.")
            elif row["location_id"] != location_id:
                raise ValueError("El local no coincide con la sesión existente.")
            elif row["status"] == "closed":
                raise ValueError("La sesión está cerrada.")
            return dict(row)

    def snapshot(self, session_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            session = connection.execute(
                "SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            messages = connection.execute(
                "SELECT message_id, role, text, status, created_at FROM chat_messages "
                "WHERE session_id = ? ORDER BY created_at, rowid",
                (session_id,),
            ).fetchall()
        return {
            "session_id": session_id,
            "agent_id": "manager_support",
            "user_id": session["user_id"],
            "location_id": session["location_id"],
            "status": session["status"],
            "created_at": session["created_at"],
            "event_sequence": session["event_sequence"],
            "messages": [dict(message) for message in messages],
        }

    def history(self, session_id: str) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT role, text, status FROM chat_messages WHERE session_id = ? "
                "ORDER BY created_at, rowid",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_message(self, session_id: str, role: str, text: str, status: str) -> str:
        message_id = f"msg_{uuid.uuid4().hex}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO chat_messages(message_id, session_id, role, text, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, session_id, role, text, status, _now()),
            )
        return message_id

    def append_text(self, message_id: str, text: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE chat_messages SET text = text || ? WHERE message_id = ?",
                (text, message_id),
            )

    def update_message_status(self, message_id: str, status: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE chat_messages SET status = ? WHERE message_id = ?",
                (status, message_id),
            )

    def update_session_status(self, session_id: str, status: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE chat_sessions SET status = ? WHERE session_id = ?",
                (status, session_id),
            )

    def recover_stale_generations(self, session_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE chat_messages SET status = 'interrupted' "
                "WHERE session_id = ? AND role = 'assistant' AND status = 'generating'",
                (session_id,),
            )
            if cursor.rowcount:
                connection.execute(
                    "UPDATE chat_sessions SET status = 'interrupted' WHERE session_id = ?",
                    (session_id,),
                )

    def next_event_sequence(self, session_id: str) -> int:
        with self._connect() as connection:
            connection.execute(
                "UPDATE chat_sessions SET event_sequence = event_sequence + 1 WHERE session_id = ?",
                (session_id,),
            )
            row = connection.execute(
                "SELECT event_sequence FROM chat_sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return row["event_sequence"]


class SessionEventBus:
    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.setdefault(f"chat.{session_id}", set()).add(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        channel = f"chat.{session_id}"
        self._subscribers.get(channel, set()).discard(queue)
        if not self._subscribers.get(channel):
            self._subscribers.pop(channel, None)

    async def publish(self, session_id: str, event: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers.get(f"chat.{session_id}", ())):
            await queue.put(event)


class SessionRuntime:
    def __init__(self):
        self.bus = SessionEventBus()
        self.generations: dict[str, asyncio.Task[None]] = {}
        self.locks: dict[str, asyncio.Lock] = {}

    def lock_for(self, session_id: str) -> asyncio.Lock:
        return self.locks.setdefault(session_id, asyncio.Lock())


store = ChatSessionStore()
runtime = SessionRuntime()


async def _publish(session_id: str, event: str, data: dict[str, Any]) -> None:
    data["session_id"] = session_id
    data["event_sequence"] = store.next_event_sequence(session_id)
    await runtime.bus.publish(session_id, {"event": event, "data": data})


async def _produce_generation(
    session: dict[str, Any],
    user_id: str,
    input_text: str,
    user_message_id: str,
    assistant_message_id: str,
    history: list[dict[str, str]],
) -> None:
    session_id = session["session_id"]
    token_sequence = 0
    emitted_text = ""
    await _publish(
        session_id,
        "generation_started",
        {"message_id": assistant_message_id, "user_message_id": user_message_id},
    )
    try:
        async for mode, chunk in stream_agent(
            input_text,
            actor_id=user_id,
            thread_id=session_id,
            conversation_history=history,
        ):
            if mode == "custom" and isinstance(chunk, dict) and chunk.get("token"):
                token = str(chunk["token"])
                store.append_text(assistant_message_id, token)
                emitted_text += token
                token_sequence += 1
                await _publish(
                    session_id,
                    "token_chunk",
                    {
                        "message_id": assistant_message_id,
                        "token": token,
                        "sequence": token_sequence,
                    },
                )
            elif mode == "values":
                answer = chunk.get("answer") if isinstance(chunk, dict) else None
                if isinstance(answer, str) and answer.startswith(emitted_text):
                    suffix = answer[len(emitted_text):]
                    for token in re.findall(r"\S+\s*", suffix):
                        store.append_text(assistant_message_id, token)
                        emitted_text += token
                        token_sequence += 1
                        await _publish(
                            session_id,
                            "token_chunk",
                            {
                                "message_id": assistant_message_id,
                                "token": token,
                                "sequence": token_sequence,
                            },
                        )
        store.update_message_status(assistant_message_id, "completed")
        store.update_session_status(session_id, "active")
        await _publish(session_id, "generation_completed", {"message_id": assistant_message_id})
    except asyncio.CancelledError:
        store.update_message_status(assistant_message_id, "interrupted")
        store.update_session_status(session_id, "interrupted")
        await _publish(
            session_id,
            "generation_interrupted",
            {"message_id": assistant_message_id, "status": "interrupted"},
        )
        raise
    except Exception:
        store.update_message_status(assistant_message_id, "failed")
        await _publish(session_id, "generation_failed", {"message_id": assistant_message_id})
    finally:
        current = runtime.generations.get(session_id)
        if current is asyncio.current_task():
            runtime.generations.pop(session_id, None)


async def _start_turn(
    session: dict[str, Any], user_id: str, text: str, *, rate_checked: bool = False
) -> None:
    session_id = session["session_id"]
    text = sanitize_user_input(text)
    if not text:
        await _publish(session_id, "chat_error", {"detail": "El mensaje no contiene texto válido."})
        return
    async with runtime.lock_for(session_id):
        active = runtime.generations.get(session_id)
        if active and not active.done():
            await _publish(session_id, "chat_error", {"detail": "Envía interrupt_requested para redirigir la respuesta."})
            return
        if not rate_checked:
            retry_after = agent_query_rate_limiter.check(f"user:{user_id}")
            if retry_after is not None:
                await _publish(
                    session_id,
                    "chat_error",
                    {"detail": f"Límite de consultas alcanzado. Reintenta en {retry_after} segundos."},
                )
                return
        store.update_session_status(session_id, "active")
        user_message_id = store.create_message(session_id, "user", text, "completed")
        await _publish(
            session_id,
            "user_message",
            {"message_id": user_message_id, "text": text, "status": "completed"},
        )
        history = store.history(session_id)[:-1]
        assistant_message_id = store.create_message(session_id, "assistant", "", "generating")
        task = asyncio.create_task(
            _produce_generation(
                session,
                user_id,
                text,
                user_message_id,
                assistant_message_id,
                history,
            )
        )
        runtime.generations[session_id] = task


async def _interrupt_and_redirect(session: dict[str, Any], user_id: str, new_input: str) -> None:
    session_id = session["session_id"]
    new_input = sanitize_user_input(new_input)
    if not new_input:
        await _publish(session_id, "chat_error", {"detail": "El mensaje no contiene texto válido."})
        return
    retry_after = agent_query_rate_limiter.check(f"user:{user_id}")
    if retry_after is not None:
        await _publish(
            session_id,
            "chat_error",
            {"detail": f"Límite de consultas alcanzado. Reintenta en {retry_after} segundos."},
        )
        return
    await _publish(session_id, "interrupt_requested", {"new_input": new_input})
    async with runtime.lock_for(session_id):
        active = runtime.generations.get(session_id)
        if active and not active.done():
            active.cancel()
    if active and not active.done():
        try:
            await active
        except asyncio.CancelledError:
            pass
    await _start_turn(session, user_id, new_input, rate_checked=True)


async def _send_events(websocket: WebSocket, queue: asyncio.Queue[dict[str, Any]]) -> None:
    while True:
        await websocket.send_json(await queue.get())


@router.websocket("/agent/chat/{session_id}")
async def manager_support_chat(
    websocket: WebSocket,
    session_id: str,
    token: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
) -> None:
    if not token or not location_id or location_id not in LOCATION_IDS or len(session_id) > 100:
        await websocket.close(code=4401 if not token else 4400)
        return
    try:
        current_user = get_current_user(token)
    except Exception:
        await websocket.close(code=4401)
        return
    try:
        session = store.open_session(session_id, current_user.id, location_id)
    except PermissionError:
        await websocket.close(code=4403)
        return
    except ValueError:
        await websocket.close(code=4400)
        return
    active_generation = runtime.generations.get(session_id)
    if active_generation is None or active_generation.done():
        store.recover_stale_generations(session_id)

    queue = runtime.bus.subscribe(session_id)
    await websocket.accept()
    snapshot = store.snapshot(session_id)
    await websocket.send_json({
        "event": "session_snapshot",
        "data": {
            "session_id": session_id,
            "agent_id": snapshot["agent_id"],
            "user_id": snapshot["user_id"],
            "location_id": snapshot["location_id"],
            "status": snapshot["status"],
            "created_at": snapshot["created_at"],
            "messages": snapshot["messages"],
            "event_sequence": snapshot["event_sequence"],
        },
    })
    sender = asyncio.create_task(_send_events(websocket, queue))
    try:
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                continue
            event = payload.get("event")
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            if data.get("session_id", session_id) != session_id:
                await _publish(session_id, "chat_error", {"detail": "La sesión del evento no coincide con el socket."})
                continue
            if event == "user_message":
                text = str(data.get("text", "")).strip()
                if text:
                    await _start_turn(session, current_user.id, text[:3000])
            elif event == "interrupt_requested":
                new_input = str(data.get("new_input", "")).strip()
                if new_input:
                    await _interrupt_and_redirect(session, current_user.id, new_input[:3000])
            elif event == "session_close":
                store.update_session_status(session_id, "closed")
                await _publish(session_id, "session_closed", {})
                break
            else:
                await _publish(session_id, "chat_error", {"detail": "Evento de chat no reconocido."})
    except WebSocketDisconnect:
        pass
    finally:
        sender.cancel()
        try:
            await sender
        except asyncio.CancelledError:
            pass
        runtime.bus.unsubscribe(session_id, queue)