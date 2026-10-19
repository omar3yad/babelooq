"""Garage edge agent.

Keeps an outbound WebSocket to the VPS (the garage is behind NAT), and for each
TRIGGER_CAPTURE: camera snapshot -> YOLO + OCR -> WebP -> CAPTURE_RESULT.

Run from the directory that contains `edge_agent/`:
    python -m edge_agent.agent
"""
import asyncio
import base64
import json
import logging
import random
import signal
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidStatus

from .camera import CameraError, SnapshotCamera
from .recognizer import PlateRecognizer, YoloOcrRecognizer, decode_image, encode_webp
from .settings import EdgeSettings

logger = logging.getLogger("edge_agent")

AGENT_VERSION = "1.0.0"
_HELLO_TIMEOUT_S = 5.0
_SEND_TIMEOUT_S = 5.0
_RECONNECT_MAX_S = 30.0
# Results that could not be sent (socket down) are retried after reconnecting;
# the server still stores late results for the session record.
_OUTBOX_MAX_AGE_S = 120.0
_OUTBOX_MAX_ITEMS = 50


class DeadlineExceeded(Exception):
    pass


class EdgeAgent:
    def __init__(
        self,
        settings: EdgeSettings,
        camera: SnapshotCamera,
        recognizer: PlateRecognizer,
    ) -> None:
        self._settings = settings
        self._camera = camera
        self._recognizer = recognizer
        # Models are not thread-safe and saturate the CPU/GPU anyway: one worker
        # thread serialises inference without ever blocking the event loop
        # (which must keep answering WebSocket pings).
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="inference")
        # One capture at a time per camera.
        self._gate_locks = {gate: asyncio.Lock() for gate in camera.gates}
        self._ws: ClientConnection | None = None
        self._send_lock = asyncio.Lock()
        self._outbox: deque[tuple[float, dict[str, Any]]] = deque(maxlen=_OUTBOX_MAX_ITEMS)
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------ connection

    async def run_forever(self) -> None:
        attempt = 0
        while True:
            try:
                async with connect(
                    self._settings.SERVER_URL,
                    additional_headers={"Authorization": f"Bearer {self._settings.API_TOKEN}"},
                    user_agent_header=f"pgms-edge-agent/{AGENT_VERSION}",
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=3,
                    max_size=1_000_000,
                ) as ws:
                    await self._handshake(ws)
                    attempt = 0
                    self._ws = ws
                    logger.info("Connected to %s as %s", self._settings.SERVER_URL, self._settings.NODE_ID)
                    await self._flush_outbox()
                    async for frame in ws:
                        self._on_frame(frame)
                logger.warning("Server closed the connection")
            except InvalidStatus as exc:
                code = exc.response.status_code
                hint = " (check EDGE_API_TOKEN)" if code in (401, 403) else ""
                logger.error("Server rejected connection: HTTP %s%s", code, hint)
            except (OSError, ConnectionClosed, InvalidHandshake, asyncio.TimeoutError, ValueError) as exc:
                logger.warning("Connection problem: %s: %s", exc.__class__.__name__, exc)
            except Exception:
                # Unattended PC: never let an unexpected error end the agent.
                logger.exception("Unexpected error in connection loop")
            finally:
                self._ws = None

            delay = min(_RECONNECT_MAX_S, 2 ** attempt) * random.uniform(0.5, 1.0)
            attempt = min(attempt + 1, 6)
            logger.info("Reconnecting in %.1fs", delay)
            await asyncio.sleep(delay)

    async def _handshake(self, ws: ClientConnection) -> None:
        await ws.send(json.dumps({
            "event": "HELLO",
            "node_id": self._settings.NODE_ID,
            "gates": self._camera.gates,
            "version": AGENT_VERSION,
        }))
        reply = json.loads(await asyncio.wait_for(ws.recv(), _HELLO_TIMEOUT_S))
        if reply.get("event") != "HELLO_ACK":
            raise ValueError(f"unexpected handshake reply: {reply.get('event')!r}")

    def _on_frame(self, frame: str | bytes) -> None:
        try:
            message = json.loads(frame)
            event = message.get("event")
        except (ValueError, AttributeError):
            logger.warning("Ignoring non-JSON frame from server")
            return

        if event == "TRIGGER_CAPTURE":
            received_at = time.monotonic()
            task = asyncio.create_task(self._process_trigger(message, received_at))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        elif event == "RESULT_ACK":
            if not message.get("accepted"):
                logger.warning(
                    "Server rejected result for session %s: %s",
                    message.get("session_id"), message.get("reason"),
                )
        elif event != "PONG":
            logger.debug("Ignoring event %r", event)

    # --------------------------------------------------------------- capture

    async def _process_trigger(self, trigger: dict[str, Any], received_at: float) -> None:
        try:
            session_id = int(trigger["session_id"])
            gate_id = int(trigger["gate_id"])
            timeout_s = max(int(trigger["timeout_ms"]), 0) / 1000
        except (KeyError, TypeError, ValueError):
            logger.warning("Malformed trigger: %r", trigger)
            return

        deadline = received_at + timeout_s
        timings: dict[str, float] = {}
        result: dict[str, Any] = {"event": "CAPTURE_RESULT", "session_id": session_id}
        lock = self._gate_locks.get(gate_id)

        try:
            if lock is None:
                raise CameraError(f"no camera configured for gate {gate_id}")
            async with lock:
                result.update(await self._capture(gate_id, deadline, timings))
        except DeadlineExceeded as exc:
            result.update(status="ERROR", error=f"deadline exceeded {exc}")
        except CameraError as exc:
            result.update(status="ERROR", error=f"camera: {exc}")
        except Exception as exc:
            logger.exception("Capture failed for session %s", session_id)
            result.update(status="ERROR", error=f"processing failed: {exc.__class__.__name__}")

        timings["total"] = _ms_since(received_at)
        result["timings_ms"] = timings
        logger.info(
            "session=%s gate=%s status=%s plate=%r timings=%s",
            session_id, gate_id, result.get("status"), result.get("plate_number"), timings,
        )
        await self._send_result(result)

    async def _capture(self, gate_id: int, deadline: float, timings: dict[str, float]) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        # A trigger that waited too long behind another capture would photograph
        # whatever car is at the gate *now*, not the one that scanned the card.
        if remaining <= 0.05:
            raise DeadlineExceeded("before snapshot")

        started = time.monotonic()
        jpeg = await self._camera.snapshot(gate_id, remaining)
        timings["snapshot"] = _ms_since(started)

        started = time.monotonic()
        loop = asyncio.get_running_loop()
        recognition, webp = await loop.run_in_executor(self._executor, self._analyse, jpeg)
        timings["analyse"] = _ms_since(started)

        return {
            "status": "SUCCESS" if recognition.plate_text else "NO_PLATE",
            "plate_number": recognition.plate_text,
            "confidence": recognition.confidence,
            "image_webp_b64": base64.b64encode(webp).decode("ascii"),
        }

    def _analyse(self, jpeg: bytes):
        """Runs in the inference thread."""
        image = decode_image(jpeg)
        recognition = self._recognizer.recognize(image)
        webp = encode_webp(image, self._settings.WEBP_MAX_WIDTH, self._settings.WEBP_QUALITY)
        return recognition, webp

    # ------------------------------------------------------------------ send

    async def _send_result(self, result: dict[str, Any]) -> None:
        if not await self._try_send(result):
            self._outbox.append((time.monotonic(), result))
            logger.warning("Result for session %s queued until reconnect", result["session_id"])

    async def _try_send(self, payload: dict[str, Any]) -> bool:
        ws = self._ws
        if ws is None:
            return False
        try:
            async with self._send_lock:
                await asyncio.wait_for(ws.send(json.dumps(payload)), _SEND_TIMEOUT_S)
            return True
        except (ConnectionClosed, asyncio.TimeoutError, OSError) as exc:
            logger.warning("Send failed: %s", exc.__class__.__name__)
            return False

    async def _flush_outbox(self) -> None:
        while self._outbox:
            queued_at, payload = self._outbox[0]
            if time.monotonic() - queued_at > _OUTBOX_MAX_AGE_S:
                self._outbox.popleft()
                logger.warning("Dropped stale result for session %s", payload["session_id"])
                continue
            if not await self._try_send(payload):
                return
            self._outbox.popleft()

    async def aclose(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._executor.shutdown(wait=False, cancel_futures=True)


def _ms_since(started: float) -> float:
    return round((time.monotonic() - started) * 1000, 1)


async def _run(settings: EdgeSettings, recognizer: PlateRecognizer) -> None:
    camera = SnapshotCamera(
        urls=settings.CAMERAS,
        auth_mode=settings.CAMERA_AUTH,
        username=settings.CAMERA_USERNAME,
        password=settings.CAMERA_PASSWORD,
        timeout_s=settings.SNAPSHOT_TIMEOUT_S,
    )
    agent = EdgeAgent(settings, camera, recognizer)
    main_task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, main_task.cancel)
        except (NotImplementedError, RuntimeError):
            pass  # Windows: Ctrl+C still raises KeyboardInterrupt
    try:
        await agent.run_forever()
    except asyncio.CancelledError:
        logger.info("Shutting down")
    finally:
        await agent.aclose()
        await camera.aclose()


def main() -> None:
    settings = EdgeSettings()
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Loading plate models (%s)...", settings.DETECTOR_WEIGHTS)
    recognizer = YoloOcrRecognizer(
        weights=settings.DETECTOR_WEIGHTS,
        ocr_langs=settings.OCR_LANGS,
        use_gpu=settings.USE_GPU,
        min_confidence=settings.MIN_DETECTION_CONFIDENCE,
    )
    started = time.monotonic()
    recognizer.warmup()
    logger.info("Models ready in %.1fs; cameras for gates %s", time.monotonic() - started, sorted(settings.CAMERAS))
    try:
        asyncio.run(_run(settings, recognizer))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
