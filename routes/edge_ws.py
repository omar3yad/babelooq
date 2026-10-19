"""WebSocket endpoint the garage edge PC keeps open (it sits behind NAT and
cannot be reached directly, so it dials out to us)."""
import asyncio
import hmac
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from config import get_settings
from database import AsyncSessionLocal
from schemas.edge import CaptureResult, EdgeHello
from services.edge_hub import EdgeConnection, EdgeHub
from services.plate_capture_service import CaptureRejected, PlateCaptureService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["edge"])

_HELLO_TIMEOUT_S = 5.0


def _authorized(websocket: WebSocket, expected: str | None) -> bool:
    if not expected:
        return False
    header = websocket.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return False
    return hmac.compare_digest(token.strip().encode(), expected.encode())


@router.websocket("/ws/edge")
async def edge_socket(websocket: WebSocket) -> None:
    settings = get_settings()
    hub: EdgeHub | None = getattr(websocket.app.state, "edge_hub", None)

    # Closing before accept() makes Starlette reject the handshake with HTTP 403.
    if hub is None or not _authorized(websocket, settings.EDGE_API_TOKEN):
        logger.warning("Rejected edge connection from %s", websocket.client)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_json(), _HELLO_TIMEOUT_S)
        hello = EdgeHello.model_validate(raw)
    except (asyncio.TimeoutError, ValidationError, ValueError, KeyError, WebSocketDisconnect) as exc:
        logger.warning("Edge handshake failed: %s", exc)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="bad hello")
        return

    conn = EdgeConnection(websocket=websocket, node_id=hello.node_id, gates=hello.gates)
    await hub.register(conn)
    try:
        await conn.send_json({"event": "HELLO_ACK", "conn_id": conn.conn_id})
        while True:
            message = await websocket.receive_text()
            await _handle_message(conn, hub, settings, message)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Edge %s connection crashed", conn.node_id)
        await conn.close(status.WS_1011_INTERNAL_ERROR, "server error")
    finally:
        await hub.unregister(conn)


async def _handle_message(conn: EdgeConnection, hub: EdgeHub, settings, message: str) -> None:
    try:
        data = json.loads(message)
        event = data.get("event")
    except (ValueError, AttributeError):
        logger.warning("Edge %s sent non-JSON frame", conn.node_id)
        return

    if event == "PING":
        await conn.send_json({"event": "PONG"})
        return
    if event != "CAPTURE_RESULT":
        logger.warning("Edge %s sent unknown event %r", conn.node_id, event)
        return

    try:
        result = CaptureResult.model_validate(data)
    except ValidationError as exc:
        logger.warning("Edge %s sent invalid result: %s", conn.node_id, exc.errors()[:3])
        await conn.send_json({
            "event": "RESULT_ACK", "session_id": data.get("session_id"),
            "accepted": False, "reason": "invalid payload",
        })
        return

    accepted, reason = True, None
    try:
        async with AsyncSessionLocal() as db:
            session = await PlateCaptureService(db, settings).record_result(result, conn.gates)
        logger.info(
            "Plate result session=%s status=%s plate=%r timings=%s",
            session.id, session.plate_capture_status, session.plate_number, result.timings_ms,
        )
    except CaptureRejected as exc:
        accepted, reason = False, str(exc)
        logger.info("Edge result for session %s rejected: %s", result.session_id, exc)
    except Exception:
        accepted, reason = False, "server error"
        logger.exception("Failed to store plate result for session %s", result.session_id)

    if accepted:
        try:
            await hub.publish_result(result.session_id)
        except Exception as exc:
            # Waiters still pick it up through their periodic DB re-check.
            logger.warning("Result notify failed for session %s: %s", result.session_id, exc)

    await conn.send_json({
        "event": "RESULT_ACK", "session_id": result.session_id,
        "accepted": accepted, "reason": reason,
    })


__all__ = ["router"]
