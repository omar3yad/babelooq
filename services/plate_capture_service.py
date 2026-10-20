"""Persistence side of the edge plate capture: dispatching triggers, storing
results/images, and expiring captures whose deadline passed."""
import asyncio
import base64
import binascii
import logging
import os
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from models.parking_session import ParkingSession, PlateCaptureStatus
from schemas.edge import CaptureResult, TriggerCapture
from services.edge_hub import EdgeHub
from services.plate_service import PlateService

logger = logging.getLogger(__name__)

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Network allowance between the VPS deadline and the budget handed to the edge,
# so the edge stops working while its result can still arrive in time.
_EDGE_NETWORK_MARGIN_MS = 500
# Results may still land shortly after the server-side deadline (4G jitter);
# they are stored for the record even though the operator view moved on.
_LATE_RESULT_STATUSES = (
    PlateCaptureStatus.PENDING.value,
    PlateCaptureStatus.TIMEOUT.value,
)
_EDGE_STATUS_MAP = {
    "SUCCESS": PlateCaptureStatus.SUCCESS,
    "NO_PLATE": PlateCaptureStatus.NO_PLATE,
    "ERROR": PlateCaptureStatus.FAILED,
}


class CaptureRejected(Exception):
    """Result refused (unknown session, wrong gate, bad image, already final)."""


class PlateCaptureService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.plate_service = PlateService()

    @property
    def image_root(self) -> str:
        root = self.settings.PLATE_IMAGE_DIR
        return root if os.path.isabs(root) else os.path.join(_APP_DIR, root)

    # -------------------------------------------------------------- dispatch

    async def start(self, session: ParkingSession, hub: EdgeHub) -> PlateCaptureStatus:
        """Mark the session as waiting for a plate and trigger the edge PC.

        Never raises: the parking session itself is already committed and must
        not be affected by camera problems.
        """
        gate_id = session.gate_number
        if hub.is_gate_online(gate_id) is False:
            await self._set_status(session, PlateCaptureStatus.OFFLINE, error="edge offline")
            return PlateCaptureStatus.OFFLINE

        await self._set_status(session, PlateCaptureStatus.PENDING, requested=True)
        timeout_ms = int(self.settings.PLATE_CAPTURE_TIMEOUT_S * 1000)
        try:
            await hub.request_capture(
                TriggerCapture(
                    session_id=session.id,
                    card_uid=session.card_code,
                    gate_id=gate_id,
                    timeout_ms=max(timeout_ms - _EDGE_NETWORK_MARGIN_MS, 300),
                )
            )
        except Exception as exc:
            logger.error("Capture dispatch failed for session %s: %s", session.id, exc)
            await self._set_status(session, PlateCaptureStatus.FAILED, error="dispatch failed")
            return PlateCaptureStatus.FAILED
        return PlateCaptureStatus.PENDING

    async def start_exit_capture(
        self,
        session: ParkingSession | int,
        hub: EdgeHub,
        gate_id: int = 2,
        card_code: str | None = None,
    ) -> bool:
        """Trigger edge PC to capture a snapshot at exit without OCR.

        Never raises: exit completion must not be affected by camera or network issues.
        """
        session_id = session if isinstance(session, int) else getattr(session, "id", 0)
        card_uid = card_code or (getattr(session, "card_code", "") if not isinstance(session, int) else "")
        timeout_ms = int(self.settings.PLATE_CAPTURE_TIMEOUT_S * 1000)
        try:
            await hub.request_capture(
                TriggerCapture(
                    session_id=session_id,
                    card_uid=str(card_uid),
                    gate_id=gate_id,
                    timeout_ms=max(timeout_ms - _EDGE_NETWORK_MARGIN_MS, 300),
                    capture_type="exit",
                    skip_ocr=True,
                )
            )
            return True
        except Exception as exc:
            logger.error("Exit capture dispatch failed for session %s: %s", session_id, exc)
            return False

    async def _set_status(
        self,
        session: ParkingSession,
        status: PlateCaptureStatus,
        error: str | None = None,
        requested: bool = False,
    ) -> None:
        session.plate_capture_status = status.value
        session.plate_capture_error = error
        if requested:
            session.plate_capture_requested_at = datetime.utcnow()
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Could not persist capture status for session %s", session.id)

    # ---------------------------------------------------------------- result

    async def record_result(self, result: CaptureResult, allowed_gates: list[int]) -> ParkingSession:
        session = await self._get(result.session_id)
        if session is None:
            raise CaptureRejected("unknown session")

        # Handle exit snapshot without OCR
        is_exit_capture = (
            getattr(result, "capture_type", "entry") == "exit"
            or session.exit_time is not None
            or (session.plate_image_path is not None and session.exit_image_path is None)
        )
        if is_exit_capture:
            image_bytes, ext = self._decode_image(result.image_webp_b64)
            rel_path = None
            if image_bytes is not None:
                rel_path = self._build_image_path(session.id, ext or ".jpg", suffix="_exit")
                await asyncio.to_thread(self._write_atomic, rel_path, image_bytes)
                await self.db.execute(
                    update(ParkingSession)
                    .where(ParkingSession.id == session.id)
                    .values(exit_image_path=rel_path)
                )
                await self.db.commit()
            return await self._get(session.id)

        if session.gate_number not in allowed_gates:
            raise CaptureRejected("session belongs to another gate")
        if session.plate_capture_status not in _LATE_RESULT_STATUSES:
            raise CaptureRejected(f"capture already {session.plate_capture_status}")

        image_bytes, ext = self._decode_image(result.image_webp_b64)
        rel_path = None
        if image_bytes is not None:
            rel_path = self._build_image_path(session.id, ext or ".jpg")
            await asyncio.to_thread(self._write_atomic, rel_path, image_bytes)

        status = _EDGE_STATUS_MAP[result.status]
        plate = self.plate_service.normalize(result.plate_number or "")[:30] or None
        if status is PlateCaptureStatus.SUCCESS and plate is None:
            status = PlateCaptureStatus.NO_PLATE

        values = {
            "plate_capture_status": status.value,
            "plate_captured_at": datetime.utcnow(),
            "plate_confidence": result.confidence,
            "plate_image_path": rel_path,
            "plate_capture_error": (result.error or None) if status is PlateCaptureStatus.FAILED else None,
        }
        # Conditional update: two concurrent results (duplicate edge connection)
        # cannot both win, and an operator-typed plate is never overwritten.
        stmt = (
            update(ParkingSession)
            .where(
                ParkingSession.id == session.id,
                ParkingSession.plate_capture_status.in_(_LATE_RESULT_STATUSES),
            )
            .values(**values)
        )
        try:
            updated = (await self.db.execute(stmt)).rowcount
            if updated and plate and status is PlateCaptureStatus.SUCCESS:
                await self.db.execute(
                    update(ParkingSession)
                    .where(ParkingSession.id == session.id, ParkingSession.plate_number.is_(None))
                    .values(plate_number=plate)
                )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            self._remove_quietly(rel_path)
            raise

        if not updated:
            self._remove_quietly(rel_path)
            raise CaptureRejected("capture finalised concurrently")
        return await self._get(session.id)

    def _decode_image(self, b64: str | None) -> tuple[bytes, str] | tuple[None, None]:
        if not b64:
            return None, None
        try:
            data = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError):
            raise CaptureRejected("image is not valid base64")
        if len(data) > self.settings.PLATE_IMAGE_MAX_BYTES:
            raise CaptureRejected("image too large")
        is_jpeg = len(data) >= 3 and data[:3] == b"\xff\xd8\xff"
        is_webp = len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
        if not (is_jpeg or is_webp):
            raise CaptureRejected("image is not JPEG or WebP")
        ext = ".jpg" if is_jpeg else ".webp"
        return data, ext

    @staticmethod
    def _build_image_path(session_id: int, ext: str = ".jpg", suffix: str = "") -> str:
        day = datetime.utcnow()
        return os.path.join(
            f"{day:%Y}", f"{day:%m}", f"{day:%d}", f"{session_id}{suffix}_{uuid.uuid4().hex[:8]}{ext}"
        )

    def _write_atomic(self, rel_path: str, data: bytes) -> None:
        abs_path = os.path.join(self.image_root, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        tmp_path = f"{abs_path}.tmp"
        with open(tmp_path, "wb") as fh:
            fh.write(data)
        os.replace(tmp_path, abs_path)

    def _remove_quietly(self, rel_path: str | None) -> None:
        if rel_path:
            try:
                os.remove(os.path.join(self.image_root, rel_path))
            except OSError:
                pass

    def resolve_image(self, rel_path: str | None) -> str | None:
        """Absolute path of a stored image, refusing anything outside image_root."""
        if not rel_path:
            return None
        root = os.path.realpath(self.image_root)
        abs_path = os.path.realpath(os.path.join(root, rel_path))
        if os.path.commonpath([root, abs_path]) != root or not os.path.isfile(abs_path):
            return None
        return abs_path

    # ---------------------------------------------------------------- polling

    async def get_fresh(self, session_id: int) -> ParkingSession | None:
        """Reload from the DB (bypassing the identity map), expiring the capture
        if its deadline has passed, then release the connection back to the pool
        so a long-poll does not pin it while waiting."""
        session = await self._get(session_id)
        if session is not None and self._is_overdue(session):
            await self.db.execute(
                update(ParkingSession)
                .where(
                    ParkingSession.id == session_id,
                    ParkingSession.plate_capture_status == PlateCaptureStatus.PENDING.value,
                )
                .values(plate_capture_status=PlateCaptureStatus.TIMEOUT.value,
                        plate_capture_error="no result before deadline")
            )
            await self.db.commit()
            session = await self._get(session_id)
        await self.db.commit()
        return session

    def remaining_s(self, session: ParkingSession) -> float:
        if session.plate_capture_requested_at is None:
            return 0.0
        deadline = session.plate_capture_requested_at + timedelta(
            seconds=self.settings.PLATE_CAPTURE_TIMEOUT_S
        )
        return max((deadline - datetime.utcnow()).total_seconds(), 0.0)

    def _is_overdue(self, session: ParkingSession) -> bool:
        return (
            session.plate_capture_status == PlateCaptureStatus.PENDING.value
            and self.remaining_s(session) <= 0
        )

    async def _get(self, session_id: int) -> ParkingSession | None:
        result = await self.db.execute(
            select(ParkingSession)
            .where(ParkingSession.id == session_id)
            .execution_options(populate_existing=True)
            .limit(1)
        )
        return result.scalars().first()


def capture_payload(session: ParkingSession, image_url: str | None) -> dict:
    """JSON shape consumed by static/js/dashboard.js."""
    status = session.plate_capture_status
    return {
        "status": status,
        "plate_number": session.plate_number if status == PlateCaptureStatus.SUCCESS.value else None,
        "confidence": session.plate_confidence,
        "image_url": image_url if session.plate_image_path else None,
        "error": session.plate_capture_error,
    }


__all__ = ["PlateCaptureService", "CaptureRejected", "capture_payload"]
