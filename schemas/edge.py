"""WebSocket protocol between the VPS and the garage edge PC.

Edge -> VPS:  HELLO, CAPTURE_RESULT, PING
VPS -> Edge:  HELLO_ACK, TRIGGER_CAPTURE, RESULT_ACK, PONG
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class EdgeHello(BaseModel):
    event: Literal["HELLO"]
    node_id: str = Field(min_length=1, max_length=64)
    gates: list[int] = Field(min_length=1, max_length=16)
    version: str = Field(default="unknown", max_length=32)

    @field_validator("gates")
    @classmethod
    def _positive_unique(cls, gates: list[int]) -> list[int]:
        if any(g < 1 for g in gates):
            raise ValueError("gate ids must be positive")
        return sorted(set(gates))


class CaptureResult(BaseModel):
    event: Literal["CAPTURE_RESULT"]
    session_id: int = Field(gt=0)
    status: Literal["SUCCESS", "NO_PLATE", "ERROR"]
    plate_number: str | None = Field(default=None, max_length=64)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    # Base64 WebP. ~1.5 MB decoded cap is enforced again after decoding.
    image_webp_b64: str | None = Field(default=None, max_length=2_100_000)
    error: str | None = Field(default=None, max_length=255)
    timings_ms: dict[str, float] | None = None


class TriggerCapture(BaseModel):
    event: Literal["TRIGGER_CAPTURE"] = "TRIGGER_CAPTURE"
    session_id: int
    card_uid: str
    gate_id: int
    # Relative budget (not an absolute timestamp) so clock skew between the VPS
    # and the edge PC cannot shrink or extend it.
    timeout_ms: int


__all__ = ["EdgeHello", "CaptureResult", "TriggerCapture"]
