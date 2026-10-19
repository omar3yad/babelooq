from services.edge_hub import EdgeHub
from services.event_bus import LocalEventBus


async def test_presence_unknown_until_ttl_then_offline():
    hub = EdgeHub(LocalEventBus(), presence_ttl_s=30)
    assert hub.is_gate_online(1) is None
    hub._started_at -= 31
    assert hub.is_gate_online(1) is False


async def test_presence_heartbeat_marks_gate_online():
    hub = EdgeHub(LocalEventBus(), presence_ttl_s=30)
    hub._started_at -= 31
    await hub._on_presence({"conn_id": "a", "gates": [1], "online": True})
    assert hub.is_gate_online(1) is True
    assert hub.is_gate_online(2) is False


async def test_stale_offline_from_old_connection_is_ignored():
    hub = EdgeHub(LocalEventBus(), presence_ttl_s=30)
    hub._started_at -= 31
    await hub._on_presence({"conn_id": "old", "gates": [1], "online": True})
    # Edge reconnected (to another worker) before the old socket's close was seen.
    await hub._on_presence({"conn_id": "new", "gates": [1], "online": True})
    await hub._on_presence({"conn_id": "old", "gates": [1], "online": False})
    assert hub.is_gate_online(1) is True
    await hub._on_presence({"conn_id": "new", "gates": [1], "online": False})
    assert hub.is_gate_online(1) is False


async def test_result_wakes_registered_waiters_only():
    hub = EdgeHub(LocalEventBus(), presence_ttl_s=30)
    async with hub.result_waiter(7) as seven, hub.result_waiter(8) as eight:
        await hub._on_result({"session_id": 7})
        assert seven.is_set() and not eight.is_set()
    assert hub._waiters == {}
