"""Edge PC connection hub.

Each worker keeps the WebSockets that happen to be attached to it, and a
cluster-wide *presence* view built from heartbeats every worker broadcasts over
the event bus. A capture trigger is broadcast to all workers; only the worker
holding the socket for that gate forwards it.
"""
import asyncio
import logging
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from fastapi import WebSocket

from schemas.edge import TriggerCapture
from services.event_bus import EventBus

logger = logging.getLogger(__name__)

CHANNEL_TRIGGER = "pgms_edge_trigger"
CHANNEL_RESULT = "pgms_edge_result"
CHANNEL_PRESENCE = "pgms_edge_presence"

_SEND_TIMEOUT_S = 2.0


@dataclass(eq=False)
class EdgeConnection:
    websocket: WebSocket
    node_id: str
    gates: list[int]
    conn_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    _send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send_json(self, payload: dict[str, Any]) -> None:
        # Starlette WebSockets are not safe for concurrent sends: triggers arrive
        # from bus tasks while the receive loop sends acks.
        async with self._send_lock:
            await asyncio.wait_for(self.websocket.send_json(payload), _SEND_TIMEOUT_S)

    async def close(self, code: int, reason: str) -> None:
        try:
            await asyncio.wait_for(self.websocket.close(code=code, reason=reason), 2.0)
        except Exception:
            pass


class EdgeHub:
    def __init__(
        self,
        bus: EventBus,
        presence_ttl_s: float = 30.0,
        heartbeat_interval_s: float = 10.0,
    ) -> None:
        if heartbeat_interval_s * 2 >= presence_ttl_s:
            raise ValueError("presence TTL must exceed two heartbeat intervals")
        self._bus = bus
        self._presence_ttl_s = presence_ttl_s
        self._heartbeat_interval_s = heartbeat_interval_s
        self._local: dict[int, EdgeConnection] = {}
        # gate_id -> (conn_id, monotonic time last seen), cluster-wide
        self._presence: dict[int, tuple[str, float]] = {}
        self._waiters: dict[int, set[asyncio.Event]] = defaultdict(set)
        self._started_at = time.monotonic()
        self._heartbeat_task: asyncio.Task | None = None

        bus.subscribe(CHANNEL_TRIGGER, self._on_trigger)
        bus.subscribe(CHANNEL_RESULT, self._on_result)
        bus.subscribe(CHANNEL_PRESENCE, self._on_presence)

    async def start(self) -> None:
        self._started_at = time.monotonic()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            await asyncio.gather(self._heartbeat_task, return_exceptions=True)
        for conn in set(self._local.values()):
            await conn.close(1001, "server shutting down")
        self._local.clear()

    # ------------------------------------------------------------------ edges

    async def register(self, conn: EdgeConnection) -> None:
        for gate in conn.gates:
            previous = self._local.get(gate)
            if previous is not None and previous is not conn:
                logger.warning(
                    "Gate %s: edge %s replaced by %s", gate, previous.node_id, conn.node_id
                )
                await previous.close(4000, "replaced by newer connection")
            self._local[gate] = conn
        logger.info("Edge %s connected for gates %s", conn.node_id, conn.gates)
        await self._publish_presence(conn, online=True)

    async def unregister(self, conn: EdgeConnection) -> None:
        owned = [g for g in conn.gates if self._local.get(g) is conn]
        for gate in owned:
            del self._local[gate]
        logger.info("Edge %s disconnected (gates %s)", conn.node_id, owned)
        if owned:
            await self._publish_presence(conn, online=False, gates=owned)

    def is_gate_online(self, gate_id: int) -> bool | None:
        """True/False when known; None while this worker is younger than the
        presence TTL and simply has not heard a heartbeat yet."""
        if gate_id in self._local:
            return True
        entry = self._presence.get(gate_id)
        now = time.monotonic()
        if entry is not None and now - entry[1] <= self._presence_ttl_s:
            return True
        if now - self._started_at < self._presence_ttl_s:
            return None
        return False

    # --------------------------------------------------------------- captures

    async def request_capture(self, trigger: TriggerCapture) -> None:
        await self._bus.publish(CHANNEL_TRIGGER, trigger.model_dump())

    async def publish_result(self, session_id: int) -> None:
        await self._bus.publish(CHANNEL_RESULT, {"session_id": session_id})

    @asynccontextmanager
    async def result_waiter(self, session_id: int) -> AsyncIterator[asyncio.Event]:
        """Register *before* reading the DB so a result landing between the read
        and the wait is never missed."""
        event = asyncio.Event()
        self._waiters[session_id].add(event)
        try:
            yield event
        finally:
            waiters = self._waiters.get(session_id)
            if waiters is not None:
                waiters.discard(event)
                if not waiters:
                    del self._waiters[session_id]

    # ------------------------------------------------------------ bus handlers

    async def _on_trigger(self, payload: dict[str, Any]) -> None:
        trigger = TriggerCapture.model_validate(payload)
        conn = self._local.get(trigger.gate_id)
        if conn is None:
            return  # another worker owns this gate's socket
        try:
            await conn.send_json(trigger.model_dump())
        except Exception as exc:
            logger.error(
                "Failed to forward capture for session %s to edge %s: %s",
                trigger.session_id, conn.node_id, exc,
            )
            await conn.close(1011, "send failed")

    async def _on_result(self, payload: dict[str, Any]) -> None:
        session_id = payload.get("session_id")
        for event in self._waiters.get(session_id, ()):
            event.set()

    async def _on_presence(self, payload: dict[str, Any]) -> None:
        conn_id = payload.get("conn_id")
        gates = payload.get("gates") or []
        now = time.monotonic()
        for gate in gates:
            if payload.get("online"):
                self._presence[gate] = (conn_id, now)
            else:
                current = self._presence.get(gate)
                # Ignore a stale "offline" when the edge already reconnected elsewhere.
                if current is not None and current[0] == conn_id:
                    del self._presence[gate]

    # --------------------------------------------------------------- presence

    async def _publish_presence(
        self, conn: EdgeConnection, online: bool, gates: list[int] | None = None
    ) -> None:
        try:
            await self._bus.publish(
                CHANNEL_PRESENCE,
                {
                    "conn_id": conn.conn_id,
                    "node_id": conn.node_id,
                    "gates": gates if gates is not None else conn.gates,
                    "online": online,
                },
            )
        except Exception as exc:
            logger.warning("Failed to publish edge presence: %s", exc)

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval_s)
            for conn in set(self._local.values()):
                owned = [g for g in conn.gates if self._local.get(g) is conn]
                if owned:
                    await self._publish_presence(conn, online=True, gates=owned)


__all__ = [
    "EdgeHub",
    "EdgeConnection",
    "CHANNEL_TRIGGER",
    "CHANNEL_RESULT",
    "CHANNEL_PRESENCE",
]
