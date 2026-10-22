"""Process-local fan-out for live RFP ticket events."""

from __future__ import annotations

import asyncio
import json
from typing import Any


RFP_TICKET_CREATED = "rfp_ticket_created"


class RFPEventBroker:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            queue.put_nowait(event)


def encode_sse_event(event_name: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_name}\ndata: {data}\n\n"


rfp_event_broker = RFPEventBroker()