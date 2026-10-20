"""Garage edge agent for Babelooq smart parking.

Keeps an outbound WebSocket to the VPS (behind NAT), and for each
TRIGGER_CAPTURE: camera snapshot -> Egyptian YOLO + OCR -> JPEG/WebP -> CAPTURE_RESULT.
Also saves local dataset for model training continuously.

Run from the directory that contains `edge_agent/`:
    python -m edge_agent.agent
"""
import asyncio
import base64
import csv
import json
import logging
import os
import random
import re
import signal
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Any

from PIL import Image
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake, InvalidStatus

from .camera import CameraError, SnapshotCamera
from .recognizer import EgyptianPlateRecognizer, Recognition, decode_image, encode_jpeg, encode_webp
from .settings import EdgeSettings

logger = logging.getLogger("edge_agent")

AGENT_VERSION = "1.0.0"
_HELLO_TIMEOUT_S = 5.0
_SEND_TIMEOUT_S = 5.0
_RECONNECT_MAX_S = 30.0
_OUTBOX_MAX_AGE_S = 120.0
_OUTBOX_MAX_ITEMS = 50


class DeadlineExceeded(Exception):
    pass


class EdgeAgent:
    def __init__(
        self,
        settings: EdgeSettings,
        camera: SnapshotCamera,
        recognizer: EgyptianPlateRecognizer,
    ) -> None:
        self._settings = settings
        self._camera = camera
        self._recognizer = recognizer
        self._ws: ClientConnection | None = None
        self._send_lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="edge-inf")
        self._gate_locks = {g: asyncio.Lock() for g in camera.gates}
        self._outbox: deque[tuple[float, dict[str, Any]]] = deque(maxlen=_OUTBOX_MAX_ITEMS)

    # ------------------------------------------------------------- lifecycle

    async def run_forever(self) -> None:
        attempt = 0
        while True:
            try:
                await self._connect_once()
                attempt = 0
            except (ConnectionClosed, InvalidHandshake, InvalidStatus, OSError) as exc:
                logger.warning("Connection dropped (%s): %s", exc.__class__.__name__, exc)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error in connection loop")
            finally:
                self._ws = None

            delay = min(_RECONNECT_MAX_S, 2 ** attempt) * random.uniform(0.5, 1.0)
            attempt = min(attempt + 1, 6)
            logger.info("Reconnecting in %.1fs", delay)
            await asyncio.sleep(delay)

    async def _connect_once(self) -> None:
        headers = {"Authorization": f"Bearer {self._settings.API_TOKEN}"}
        logger.info("Connecting to %s", self._settings.SERVER_URL)
        async with connect(
            self._settings.SERVER_URL,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
            max_size=2_000_000,
        ) as ws:
            self._ws = ws
            await self._handshake(ws)
            logger.info("Connected and registered gates %s", self._camera.gates)
            await self._flush_outbox()
            async for frame in ws:
                self._on_frame(frame)

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
            else:
                logger.info("Server acknowledged result for session %s", message.get("session_id"))
        elif event != "PONG":
            logger.debug("Ignoring event %r", event)

    # --------------------------------------------------------------- capture

    async def _process_trigger(self, trigger: dict[str, Any], received_at: float) -> None:
        try:
            session_id = int(trigger["session_id"])
            gate_id = int(trigger["gate_id"])
            timeout_s = max(int(trigger.get("timeout_ms", 3000)), 0) / 1000
        except (KeyError, TypeError, ValueError):
            logger.warning("Malformed trigger: %r", trigger)
            return

        deadline = received_at + timeout_s
        timings: dict[str, float] = {}
        skip_ocr = bool(trigger.get("skip_ocr") or trigger.get("capture_type") == "exit")
        capture_type = str(trigger.get("capture_type") or "entry")
        result: dict[str, Any] = {"event": "CAPTURE_RESULT", "session_id": session_id, "capture_type": capture_type}
        lock = self._gate_locks.get(gate_id)
        active_gate_id = gate_id
        if lock is None and self._gate_locks:
            active_gate_id = next(iter(self._gate_locks.keys()))
            lock = self._gate_locks[active_gate_id]
            logger.info("Gate %s has no camera lock, falling back to gate %s camera", gate_id, active_gate_id)

        try:
            if lock is None:
                raise CameraError(f"no camera configured for gate {gate_id}")
            async with lock:
                result.update(await self._capture(active_gate_id, session_id, deadline, timings, skip_ocr=skip_ocr, capture_type=capture_type))
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
            "[CAPTURE RESULT] session=%s gate=%s type=%s status=%s plate=%r timings=%s",
            session_id, gate_id, capture_type, result.get("status"), result.get("plate_number"), timings,
        )
        await self._send_result(result)

    async def _capture(
        self,
        gate_id: int,
        session_id: int,
        deadline: float,
        timings: dict[str, float],
        skip_ocr: bool = False,
        capture_type: str = "entry",
    ) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        if remaining <= 0.05:
            raise DeadlineExceeded("before snapshot")

        started = time.monotonic()
        jpeg = await self._camera.snapshot(gate_id, remaining)
        timings["snapshot"] = _ms_since(started)

        started = time.monotonic()
        loop = asyncio.get_running_loop()
        if skip_ocr:
            recognition, encoded_img = await loop.run_in_executor(
                self._executor,
                partial(self._encode_snapshot_only, jpeg, gate_id, session_id)
            )
            timings["encode"] = _ms_since(started)
            return {
                "status": "SUCCESS",
                "capture_type": capture_type,
                "plate_number": None,
                "confidence": None,
                "image_webp_b64": base64.b64encode(encoded_img).decode("ascii"),
            }
        else:
            recognition, encoded_img = await loop.run_in_executor(
                self._executor,
                partial(self._analyse_and_save, jpeg, gate_id, session_id)
            )
            timings["analyse"] = _ms_since(started)
            return {
                "status": "SUCCESS" if recognition.plate_text else "NO_PLATE",
                "capture_type": capture_type,
                "plate_number": recognition.plate_text,
                "confidence": recognition.confidence,
                "image_webp_b64": base64.b64encode(encoded_img).decode("ascii"),
            }

    def _encode_snapshot_only(self, jpeg: bytes, gate_id: int, session_id: int) -> tuple[Recognition, bytes]:
        """Encodes snapshot without running AI models."""
        image = decode_image(jpeg)
        recognition = Recognition(plate_text=None, confidence=None)
        if self._settings.IMAGE_FORMAT == "webp":
            encoded_img = encode_webp(image, self._settings.WEBP_MAX_WIDTH, self._settings.WEBP_QUALITY)
        else:
            encoded_img = encode_jpeg(image, self._settings.WEBP_MAX_WIDTH, self._settings.JPEG_QUALITY)
        return recognition, encoded_img

    def _analyse_and_save(self, jpeg: bytes, gate_id: int, session_id: int) -> tuple[Recognition, bytes]:
        """Runs in the inference thread."""
        image = decode_image(jpeg)
        recognition = self._recognizer.recognize(image)

        # Legacy browser compatibility (IE/IE mode): encode as JPEG by default
        if self._settings.IMAGE_FORMAT == "webp":
            encoded_img = encode_webp(image, self._settings.WEBP_MAX_WIDTH, self._settings.WEBP_QUALITY)
        else:
            encoded_img = encode_jpeg(image, self._settings.WEBP_MAX_WIDTH, self._settings.JPEG_QUALITY)

        # Dataset preservation: save full car image and plate crop for AI training
        if self._settings.SAVE_LOCAL_DATASET:
            try:
                self._save_training_data(image, recognition, gate_id, session_id)
            except Exception as e:
                logger.warning("Failed to save local dataset copy: %s", e)

        return recognition, encoded_img

    def _save_training_data(self, image: Image.Image, rec: Recognition, gate_id: int, session_id: int) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        safe_plate = re.sub(r"[^\w\-]", "_", rec.plate_text or "NO_PLATE")
        gate_dir = os.path.join(self._settings.DATASET_DIR, f"gate_{gate_id}")
        os.makedirs(os.path.join(gate_dir, "cars"), exist_ok=True)
        os.makedirs(os.path.join(gate_dir, "plates"), exist_ok=True)

        car_path = os.path.join(gate_dir, "cars", f"{timestamp}_sess{session_id}_{safe_plate}.jpg")
        image.save(car_path, format="JPEG", quality=90)

        plate_path = ""
        if rec.plate_crop is not None and rec.plate_crop.size > 0:
            plate_path = os.path.join(gate_dir, "plates", f"{timestamp}_sess{session_id}_{safe_plate}.jpg")
            crop_img = Image.fromarray(rec.plate_crop)
            crop_img.save(plate_path, format="JPEG", quality=95)

        # Log to index CSV
        index_csv = os.path.join(self._settings.DATASET_DIR, "dataset_index.csv")
        file_exists = os.path.exists(index_csv)
        with open(index_csv, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "session_id", "gate_id", "plate_text", "confidence", "car_image", "plate_image"])
            writer.writerow([timestamp, session_id, gate_id, rec.plate_text or "", rec.confidence, car_path, plate_path])

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


async def _run(settings: EdgeSettings, recognizer: EgyptianPlateRecognizer) -> None:
    camera = SnapshotCamera(
        urls=settings.CAMERAS,
        auth_mode=settings.CAMERA_AUTH,
        username=settings.CAMERA_USERNAME,
        password=settings.CAMERA_PASSWORD,
        timeout_s=settings.SNAPSHOT_TIMEOUT_S,
    )
    agent = EdgeAgent(settings, camera, recognizer)
    try:
        await agent.run_forever()
    except asyncio.CancelledError:
        logger.info("Shutting down agent...")
    finally:
        await agent.aclose()
        await camera.aclose()


def main() -> None:
    settings = EdgeSettings()
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("==================================================================")
    logger.info(" BABELOOQ EDGE AGENT - SMART PARKING PLATE RECOGNITION ")
    logger.info("==================================================================")
    logger.info("Loading Egyptian Plate Models on CUDA: %s...", settings.USE_GPU)
    recognizer = EgyptianPlateRecognizer(
        detector_weights=settings.DETECTOR_WEIGHTS,
        ocr_weights=settings.OCR_WEIGHTS,
        use_gpu=settings.USE_GPU,
        min_confidence=settings.MIN_DETECTION_CONFIDENCE,
    )
    started = time.monotonic()
    recognizer.warmup()
    logger.info("Models initialized in %.2fs. Configured gates: %s", time.monotonic() - started, sorted(settings.CAMERAS))
    try:
        asyncio.run(_run(settings, recognizer))
    except KeyboardInterrupt:
        logger.info("Stopped by user.")


if __name__ == "__main__":
    main()
