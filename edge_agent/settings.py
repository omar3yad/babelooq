from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EdgeSettings(BaseSettings):
    """All values come from EDGE_* environment variables or edge_agent/.env."""

    model_config = SettingsConfigDict(
        env_prefix="EDGE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    SERVER_URL: str = "wss://babelooq.garage4u.io/ws/edge"
    API_TOKEN: str = Field(min_length=32)
    NODE_ID: str = "garage-edge-1"

    # gate_id -> camera HTTP snapshot URL, as JSON:
    # EDGE_CAMERAS={"1": "http://192.168.1.64/ISAPI/Streaming/channels/101/picture"}
    CAMERAS: dict[int, str]
    CAMERA_AUTH: Literal["none", "basic", "digest"] = "digest"
    CAMERA_USERNAME: str | None = None
    CAMERA_PASSWORD: str | None = None
    SNAPSHOT_TIMEOUT_S: float = Field(default=0.8, gt=0, le=5)

    DETECTOR_WEIGHTS: str = "models/plate_yolo.pt"
    OCR_LANGS: list[str] = ["ar"]
    USE_GPU: bool = False
    MIN_DETECTION_CONFIDENCE: float = Field(default=0.35, ge=0, le=1)

    WEBP_QUALITY: int = Field(default=70, ge=10, le=100)
    WEBP_MAX_WIDTH: int = Field(default=1024, ge=320, le=4096)

    LOG_LEVEL: str = "INFO"

    @field_validator("CAMERAS")
    @classmethod
    def _non_empty(cls, cameras: dict[int, str]) -> dict[int, str]:
        if not cameras:
            raise ValueError("at least one camera must be configured")
        return cameras

    @field_validator("SERVER_URL")
    @classmethod
    def _websocket_scheme(cls, url: str) -> str:
        if not url.startswith(("wss://", "ws://")):
            raise ValueError("SERVER_URL must start with wss:// (or ws:// for local testing)")
        return url
