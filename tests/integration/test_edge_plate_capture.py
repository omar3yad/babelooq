"""End-to-end: edge WebSocket <-> operator scan <-> long-poll.

Uses a dedicated app instance (in-memory SQLite + LocalEventBus) because the
real app lifespan would connect to the configured production database.
"""
import base64
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import models  # noqa: F401  (registers all tables on Base.metadata)
from config import Settings, get_settings
from database import Base, get_db
from models.parking_card import CardStatus, ParkingCard
from models.shift import Shift
from models.user import User, UserRole
from routes.edge_ws import router as edge_ws_router
from routes.ui_operator import router as ui_operator_router
from services.auth_service import AuthService
from services.edge_hub import EdgeHub
from services.event_bus import LocalEventBus

EDGE_TOKEN = "e" * 40
FAKE_WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 24
FAKE_WEBP_B64 = base64.b64encode(FAKE_WEBP).decode()
CAPTURE_TIMEOUT_S = 1.5


@pytest.fixture
def edge_env(tmp_path, monkeypatch):
    settings = Settings(
        DATABASE_URL="sqlite+aiosqlite://",
        SECRET_KEY="a" * 32,
        ENVIRONMENT="development",
        EDGE_API_TOKEN=EDGE_TOKEN,
        PLATE_CAPTURE_TIMEOUT_S=CAPTURE_TIMEOUT_S,
        PLATE_POLL_MAX_WAIT_S=5.0,
        PLATE_IMAGE_DIR=str(tmp_path / "plates"),
    )
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        bus = LocalEventBus()
        hub = EdgeHub(bus, presence_ttl_s=settings.EDGE_PRESENCE_TTL_S)
        app.state.edge_hub = hub
        await hub.start()
        yield
        await hub.stop()
        await bus.stop()
        await engine.dispose()

    async def override_get_db():
        async with factory() as session:
            yield session

    app = FastAPI(lifespan=lifespan)
    app.include_router(ui_operator_router)
    app.include_router(edge_ws_router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("routes.edge_ws.get_settings", lambda: settings)
    monkeypatch.setattr("routes.edge_ws.AsyncSessionLocal", factory)

    async def seed() -> str:
        async with factory() as db:
            user = User(
                full_name="Gate One", username="gate1", hashed_password="x",
                role=UserRole.OPERATOR, gate_number=1, is_active=True,
            )
            db.add(user)
            await db.flush()
            db.add(Shift(operator_id=user.id, gate_number=1, started_at=datetime.utcnow(), opening_cash_egp=0))
            db.add_all([ParkingCard(card_code=f"CARD-{i}", status=CardStatus.AVAILABLE) for i in range(1, 6)])
            await db.commit()
            return AuthService(settings).create_access_token(user.id, user.role.value)

    with TestClient(app) as client:
        client.cookies.set("pgms_token", client.portal.call(seed))
        yield SimpleNamespace(client=client, app=app, settings=settings, image_dir=tmp_path / "plates")


def connect_edge(client: TestClient, gates=(1,), token=EDGE_TOKEN):
    ws = client.websocket_connect("/ws/edge", headers={"Authorization": f"Bearer {token}"})
    session = ws.__enter__()
    session.send_json({"event": "HELLO", "node_id": "edge-test", "gates": list(gates)})
    assert session.receive_json()["event"] == "HELLO_ACK"
    return ws, session


def scan(client: TestClient, card: str) -> dict:
    response = client.post("/ui/operator/api/scan", json={"card_code": card})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True and body["type"] == "entry"
    return body


def test_full_capture_flow_wakes_long_poll(edge_env):
    client = edge_env.client
    ctx, edge = connect_edge(client)
    try:
        body = scan(client, "CARD-1")
        capture = body["plate_capture"]
        assert capture["status"] == "PENDING"
        assert capture["timeout_ms"] == int(CAPTURE_TIMEOUT_S * 1000)

        trigger = edge.receive_json()
        assert trigger["event"] == "TRIGGER_CAPTURE"
        assert trigger["session_id"] == body["session_id"]
        assert trigger["card_uid"] == "CARD-1"
        assert trigger["gate_id"] == 1
        assert 0 < trigger["timeout_ms"] < CAPTURE_TIMEOUT_S * 1000

        # Long-poll in parallel; it must be woken by the result, not the deadline.
        poll: dict = {}

        def long_poll():
            started = time.monotonic()
            poll["body"] = client.get(capture["poll_url"] + "?wait=1").json()
            poll["elapsed"] = time.monotonic() - started

        poller = threading.Thread(target=long_poll)
        poller.start()
        time.sleep(0.2)
        edge.send_json({
            "event": "CAPTURE_RESULT", "session_id": trigger["session_id"],
            "status": "SUCCESS", "plate_number": " ب  ن ر ١٢٣٤ ", "confidence": 0.91,
            "image_webp_b64": FAKE_WEBP_B64,
        })
        ack = edge.receive_json()
        assert ack == {"event": "RESULT_ACK", "session_id": trigger["session_id"], "accepted": True, "reason": None}
        poller.join(5)

        assert poll["body"]["status"] == "SUCCESS"
        assert poll["body"]["plate_number"] == "ب ن ر 1234"
        assert poll["body"]["confidence"] == 0.91
        assert poll["elapsed"] < 1.0

        image = client.get(poll["body"]["image_url"])
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/webp"
        assert image.content == FAKE_WEBP

        # Duplicate result for an already-final capture is refused.
        edge.send_json({"event": "CAPTURE_RESULT", "session_id": trigger["session_id"], "status": "NO_PLATE"})
        assert edge.receive_json()["accepted"] is False
    finally:
        ctx.__exit__(None, None, None)


def test_timeout_then_late_result_is_still_stored(edge_env):
    client = edge_env.client
    ctx, edge = connect_edge(client)
    try:
        body = scan(client, "CARD-2")
        trigger = edge.receive_json()

        started = time.monotonic()
        result = client.get(body["plate_capture"]["poll_url"] + "?wait=1").json()
        assert result["status"] == "TIMEOUT"
        assert CAPTURE_TIMEOUT_S - 0.3 <= time.monotonic() - started < CAPTURE_TIMEOUT_S + 1.5

        edge.send_json({
            "event": "CAPTURE_RESULT", "session_id": trigger["session_id"],
            "status": "SUCCESS", "plate_number": "س ص 55", "confidence": 0.8,
        })
        assert edge.receive_json()["accepted"] is True
        late = client.get(body["plate_capture"]["poll_url"]).json()
        assert late["status"] == "SUCCESS" and late["plate_number"] == "س ص 55"
    finally:
        ctx.__exit__(None, None, None)


def test_offline_when_no_edge_connected(edge_env):
    # Pretend this worker has been up longer than the presence TTL.
    edge_env.app.state.edge_hub._started_at -= edge_env.settings.EDGE_PRESENCE_TTL_S + 1
    body = scan(edge_env.client, "CARD-3")
    assert body["plate_capture"]["status"] == "OFFLINE"
    status = edge_env.client.get(body["plate_capture"]["poll_url"] + "?wait=1").json()
    assert status["status"] == "OFFLINE"


def test_edge_cannot_write_other_gates_or_bad_images(edge_env):
    client = edge_env.client
    gate1_ctx, gate1 = connect_edge(client, gates=(1,))
    gate2_ctx, gate2 = connect_edge(client, gates=(2,))
    try:
        body = scan(client, "CARD-4")
        session_id = gate1.receive_json()["session_id"]

        gate2.send_json({"event": "CAPTURE_RESULT", "session_id": session_id, "status": "NO_PLATE"})
        assert gate2.receive_json()["reason"] == "session belongs to another gate"

        gate1.send_json({
            "event": "CAPTURE_RESULT", "session_id": session_id, "status": "SUCCESS",
            "plate_number": "أ 1", "image_webp_b64": base64.b64encode(b"\xff\xd8\xff not webp").decode(),
        })
        assert gate1.receive_json()["reason"] == "image is not WebP"
        assert client.get(body["plate_capture"]["poll_url"]).json()["status"] == "PENDING"
        assert not edge_env.image_dir.exists() or not any(edge_env.image_dir.rglob("*.webp"))
    finally:
        gate2_ctx.__exit__(None, None, None)
        gate1_ctx.__exit__(None, None, None)


def test_edge_rejected_without_valid_token(edge_env):
    with pytest.raises(WebSocketDisconnect):
        with edge_env.client.websocket_connect(
            "/ws/edge", headers={"Authorization": "Bearer wrong-token"}
        ) as ws:
            ws.receive_json()
