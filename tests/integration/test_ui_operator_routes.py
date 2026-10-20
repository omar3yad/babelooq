import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from models.user import User, UserRole
from models.parking_card import ParkingCard, CardStatus
from models.parking_session import ParkingSession, SessionStatus
from models.pricing_rule import PricingRule
from models.shift import Shift

async def setup_operator(db_session, auth_service, async_client):
    hashed = auth_service.hash_password("operatorpass")
    user = User(
        full_name="Operator User",
        username="operator1",
        hashed_password=hashed,
        role=UserRole.OPERATOR,
        gate_number=1,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    token = auth_service.create_access_token(user.id, user.role.value)
    async_client.cookies.set("pgms_token", token)
    return user

async def setup_pricing_rule(db_session):
    rule = PricingRule(
        label="Standard Rule",
        rate_per_hour=1000,
        minimum_charge=500,
        grace_period_mins=15,
        lost_card_penalty=2000,
        is_active=True,
        created_by=1,
        effective_from=datetime.utcnow()
    )
    db_session.add(rule)
    await db_session.commit()
    return rule

async def open_operator_shift(db_session, operator_id):
    shift = Shift(
        operator_id=operator_id,
        gate_number=1,
        started_at=datetime.utcnow(),
        opening_cash_egp=5000,
    )
    db_session.add(shift)
    await db_session.commit()
    return shift

@pytest.mark.asyncio
async def test_dashboard_renders(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await setup_pricing_rule(db_session)
    await open_operator_shift(db_session, op.id)
    
    response = await async_client.get("/ui/operator/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "دخول" in response.text
    assert "خروج" in response.text

@pytest.mark.asyncio
async def test_dashboard_no_shift_shows_banner(async_client, db_session, auth_service):
    await setup_operator(db_session, auth_service, async_client)
    
    response = await async_client.get("/ui/operator/dashboard")
    assert response.status_code == 200
    assert "افتح شيفتك أولاً" in response.text

@pytest.mark.asyncio
async def test_entry_page_renders(async_client, db_session, auth_service):
    await setup_operator(db_session, auth_service, async_client)
    
    response = await async_client.get("/ui/operator/entry")
    assert response.status_code == 200
    assert "scan-input" in response.text

@pytest.mark.asyncio
async def test_entry_post_success_redirects(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await setup_pricing_rule(db_session)
    await open_operator_shift(db_session, op.id)
    
    card = ParkingCard(card_code="CARD-0001", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.commit()

    response = await async_client.post(
        "/ui/operator/entry",
        data={"card_code": "CARD-0001"}
    )
    assert response.status_code == 303
    assert "/ui/operator/entry/confirm/" in response.headers.get("location", "")

@pytest.mark.asyncio
async def test_entry_post_card_not_found_rerenders(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await setup_pricing_rule(db_session)
    await open_operator_shift(db_session, op.id)

    response = await async_client.post(
        "/ui/operator/entry",
        data={"card_code": "CARD-NONEXISTENT"}
    )
    assert response.status_code == 200 # Re-renders page
    assert "الكرت ده مش مسجل في النظام" in response.text

@pytest.mark.asyncio
async def test_exit_scan_page_renders(async_client, db_session, auth_service):
    await setup_operator(db_session, auth_service, async_client)
    
    response = await async_client.get("/ui/operator/exit")
    assert response.status_code == 200
    assert "scan-input" in response.text

@pytest.mark.asyncio
async def test_exit_lookup_success(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await setup_pricing_rule(db_session)
    shift = await open_operator_shift(db_session, op.id)
    
    card = ParkingCard(card_code="CARD-0001", status=CardStatus.IN_USE)
    db_session.add(card)
    await db_session.commit()
    
    session = ParkingSession(
        card_id=card.id,
        card_code="CARD-0001",
        status=SessionStatus.ACTIVE,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        gate_number=1,
        operator_id=op.id,
        shift_id=shift.id,
    )
    db_session.add(session)
    await db_session.commit()

    response = await async_client.post(
        "/ui/operator/exit/lookup",
        data={"card_code": "CARD-0001"}
    )
    assert response.status_code == 200
    assert "تأكيد الدفع" in response.text
    assert "Standard Rule" in response.text

@pytest.mark.asyncio
async def test_receipt_page_triggers_print(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await setup_pricing_rule(db_session)
    shift = await open_operator_shift(db_session, op.id)
    
    card = ParkingCard(card_code="CARD-0001", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.commit()
    
    session = ParkingSession(
        card_id=card.id,
        card_code="CARD-0001",
        status=SessionStatus.COMPLETED,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=datetime.utcnow(),
        gate_number=1,
        operator_id=op.id,
        exit_operator_id=op.id,
        amount_charged=2000,
        shift_id=shift.id,
    )
    db_session.add(session)
    await db_session.commit()

    response = await async_client.get(f"/ui/operator/receipt/{session.id}")
    assert response.status_code == 200
    assert "window.print()" in response.text
    assert "جراج باب اللوق" in response.text

@pytest.mark.asyncio
async def test_receipt_sets_printed_at(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await setup_pricing_rule(db_session)
    shift = await open_operator_shift(db_session, op.id)
    
    card = ParkingCard(card_code="CARD-0001", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.commit()
    
    session = ParkingSession(
        card_id=card.id,
        card_code="CARD-0001",
        status=SessionStatus.COMPLETED,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=datetime.utcnow(),
        gate_number=1,
        operator_id=op.id,
        exit_operator_id=op.id,
        amount_charged=2000,
        shift_id=shift.id,
    )
    db_session.add(session)
    await db_session.commit()

    # Before call
    assert session.receipt_printed_at is None

    response = await async_client.get(f"/ui/operator/receipt/{session.id}")
    assert response.status_code == 200
    
    # After call
    await db_session.refresh(session)
    assert session.receipt_printed_at is not None

@pytest.mark.asyncio
async def test_receipt_idempotent_printed_at(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await setup_pricing_rule(db_session)
    shift = await open_operator_shift(db_session, op.id)
    
    card = ParkingCard(card_code="CARD-0001", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.commit()
    
    session = ParkingSession(
        card_id=card.id,
        card_code="CARD-0001",
        status=SessionStatus.COMPLETED,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=datetime.utcnow(),
        gate_number=1,
        operator_id=op.id,
        exit_operator_id=op.id,
        amount_charged=2000,
        shift_id=shift.id,
    )
    db_session.add(session)
    await db_session.commit()

    await async_client.get(f"/ui/operator/receipt/{session.id}")
    await db_session.refresh(session)
    first_printed_at = session.receipt_printed_at
    assert first_printed_at is not None

    # Call again
    await async_client.get(f"/ui/operator/receipt/{session.id}")
    await db_session.refresh(session)
    assert session.receipt_printed_at == first_printed_at


@pytest.mark.asyncio
async def test_entry_operator_shift_start_page_has_no_cash_field(async_client, db_session, auth_service):
    # Setup gate 1 operator
    await setup_operator(db_session, auth_service, async_client)
    res = await async_client.get("/ui/operator/shift/start")
    assert res.status_code == 200
    # Entry operator should not see opening cash input
    assert 'name="opening_cash_egp"' in res.text
    assert 'type="hidden"' in res.text
    assert "بوابة الدخول (#1)" in res.text
    assert "لا يتطلب كاش" in res.text


@pytest.mark.asyncio
async def test_entry_operator_open_shift_records_zero_cash(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    res = await async_client.post("/ui/operator/shift/start", data={})
    assert res.status_code == 303
    assert res.headers["location"] == "/ui/operator/dashboard"

    shift_res = await db_session.execute(select(Shift).where(Shift.operator_id == op.id))
    shift = shift_res.scalars().first()
    assert shift is not None
    assert shift.opening_cash_egp == 0
    assert shift.gate_number == 1


@pytest.mark.asyncio
async def test_entry_operator_shift_end_page_has_no_cash_field(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    await open_operator_shift(db_session, op.id)
    res = await async_client.get("/ui/operator/shift/end")
    assert res.status_code == 200
    assert "ملخص حركة الدخول للشيفت" in res.text
    assert "لا توجد عهدة نقدية" in res.text
    assert 'id="closing-cash-input"' not in res.text


@pytest.mark.asyncio
async def test_entry_operator_close_shift_records_zero_cash(async_client, db_session, auth_service):
    op = await setup_operator(db_session, auth_service, async_client)
    shift = await open_operator_shift(db_session, op.id)
    res = await async_client.post("/ui/operator/shift/end", data={})
    assert res.status_code == 303
    assert "/ui/login" in res.headers["location"]

    await db_session.refresh(shift)
    assert shift.ended_at is not None
    assert shift.closing_cash_egp == 0

