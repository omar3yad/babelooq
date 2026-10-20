import json
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EdgeSettings(BaseSettings):
    """All values come from EDGE_* environment variables or edge_agent/.env."""

    model_config = SettingsConfigDict(
        env_prefix="EDGE_",
        env_file=("edge_agent/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    SERVER_URL: str = "wss://babelooq.garage4u.io/ws/edge"
    API_TOKEN: str = Field(default="", min_length=32)
    NODE_ID: str = "garage-edge-1"

    # gate_id -> camera HTTP snapshot URL, as JSON or dict:
    # EDGE_CAMERAS={"1": "http://192.168.1.100/ISAPI/Streaming/channels/201/picture", "2": "http://192.168.1.100/ISAPI/Streaming/channels/101/picture"}
    CAMERAS: dict[int, str] = {
        1: "http://192.168.1.100/ISAPI/Streaming/channels/201/picture",
        2: "http://192.168.1.100/ISAPI/Streaming/channels/101/picture"
    }
    CAMERA_AUTH: Literal["none", "basic", "digest"] = "digest"
    CAMERA_USERNAME: str | None = "admin"
    CAMERA_PASSWORD: str | None = "M.H.M&F.Y.M&9620"
    SNAPSHOT_TIMEOUT_S: float = Field(default=1.0, gt=0, le=5)

    DETECTOR_WEIGHTS: str = "E:/AISystem/Models/plate_detection/best.pt"
    OCR_WEIGHTS: str = "E:/AISystem/Models/plate_recognition/best.pt"
    USE_GPU: bool = True
    MIN_DETECTION_CONFIDENCE: float = Field(default=0.25, ge=0, le=1)

    IMAGE_FORMAT: Literal["jpeg", "webp"] = "webp"
    JPEG_QUALITY: int = Field(default=80, ge=10, le=100)
    WEBP_QUALITY: int = Field(default=75, ge=10, le=100)
    WEBP_MAX_WIDTH: int = Field(default=1024, ge=320, le=4096)

    LOG_LEVEL: str = "INFO"
    SAVE_LOCAL_DATASET: bool = True
    DATASET_DIR: str = "E:/AISystem/saved_gate_images/babelooq_edge"

    @field_validator("CAMERAS", mode="before")
    @classmethod
    def _parse_cameras(cls, v):
        if isinstance(v, str):
            parsed = json.loads(v)
            return {int(k): str(val) for k, val in parsed.items()}
        if isinstance(v, dict):
            return {int(k): str(val) for k, val in v.items()}
        return v

    @field_validator("CAMERAS")
    @classmethod
    def _non_empty(cls, cameras: dict[int, str]) -> dict[int, str]:
        if not cameras:
            raise ValueError("at least one camera must be configured")
        return cameras
