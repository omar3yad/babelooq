"""Cross-worker pub/sub for the edge camera broker.

Gunicorn runs several worker processes. The edge PC's WebSocket lives in exactly
one of them, while the operator's scan request (and later the long-poll waiting
for the plate) can land on any worker. Events therefore have to cross process
boundaries:

* PostgresEventBus - LISTEN/NOTIFY on the existing database (production, no extra
  infrastructure). Payloads are tiny JSON envelopes; images never go through it.
* LocalEventBus    - in-process delivery for SQLite (development/tests, which run
  a single process).
"""
import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Awaitable, Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]

# PostgreSQL rejects NOTIFY payloads of 8000 bytes or more.
_MAX_NOTIFY_BYTES = 7900


class EventBus(ABC):
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._tasks: set[asyncio.Task] = set()

    def subscribe(self, channel: str, handler: Handler) -> None:
        """Register a handler. Must be called before start()."""
        self._handlers[channel].append(handler)

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    @abstractmethod
    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        ...

    def _dispatch_soon(self, channel: str, payload: dict[str, Any]) -> None:
        task = asyncio.create_task(self._dispatch(channel, payload))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _dispatch(self, channel: str, payload: dict[str, Any]) -> None:
        for handler in self._handlers.get(channel, ()):
            try:
                await handler(payload)
            except Exception:
                logger.exception("Event handler failed on channel %s", channel)


class LocalEventBus(EventBus):
    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        self._dispatch_soon(channel, payload)


class PostgresEventBus(EventBus):
    _RECONNECT_DELAYS_S = (0.5, 1.0, 2.0, 5.0, 10.0)
    _HEALTHCHECK_INTERVAL_S = 15.0
    _HEALTHCHECK_TIMEOUT_S = 5.0
    _CONNECT_TIMEOUT_S = 5.0

    def __init__(self, dsn: str, engine: AsyncEngine) -> None:
        super().__init__()
        self._dsn = dsn
        self._engine = engine
        self._listener_task: asyncio.Task | None = None

    async def start(self) -> None:
        # Runs in the background so a database hiccup at boot never blocks startup.
        self._listener_task = asyncio.create_task(self._listen_forever())

    async def stop(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            await asyncio.gather(self._listener_task, return_exceptions=True)
        await super().stop()

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        if len(body.encode("utf-8")) > _MAX_NOTIFY_BYTES:
            raise ValueError(f"Event payload too large for NOTIFY on {channel}")
        # Through the SQLAlchemy pool: a dedicated asyncpg connection cannot run
        # concurrent queries, and publishers here are concurrent request handlers.
        async with self._engine.begin() as conn:
            await conn.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": channel, "payload": body},
            )

    async def _listen_forever(self) -> None:
        import asyncpg

        attempt = 0
        while True:
            conn = None
            try:
                conn = await asyncpg.connect(self._dsn, timeout=self._CONNECT_TIMEOUT_S)
                for channel in self._handlers:
                    await conn.add_listener(channel, self._on_notify)
                if attempt:
                    logger.info("Event bus listener reconnected")
                attempt = 0
                while True:
                    await asyncio.sleep(self._HEALTHCHECK_INTERVAL_S)
                    await asyncio.wait_for(
                        conn.execute("SELECT 1"), self._HEALTHCHECK_TIMEOUT_S
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                delay = self._RECONNECT_DELAYS_S[
                    min(attempt, len(self._RECONNECT_DELAYS_S) - 1)
                ]
                attempt += 1
                logger.warning(
                    "Event bus listener lost (%s); reconnecting in %.1fs", exc, delay
                )
            finally:
                if conn is not None and not conn.is_closed():
                    try:
                        await asyncio.wait_for(conn.close(), 2.0)
                    except Exception:
                        conn.terminate()
            await asyncio.sleep(delay)

    def _on_notify(self, _conn: Any, _pid: int, channel: str, payload: str) -> None:
        try:
            data = json.loads(payload)
        except (TypeError, ValueError):
            logger.warning("Dropping malformed event on %s", channel)
            return
        self._dispatch_soon(channel, data)


def create_event_bus(database_url: str, engine: AsyncEngine) -> EventBus:
    if database_url.startswith("postgresql"):
        dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return PostgresEventBus(dsn, engine)
    return LocalEventBus()


__all__ = ["EventBus", "LocalEventBus", "PostgresEventBus", "create_event_bus"]
