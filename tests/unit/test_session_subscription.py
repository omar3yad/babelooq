import pytest
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from models.parking_card import ParkingCard, CardStatus
from models.user import User, UserRole
from models.subscriber import Subscriber
from models.subscription_plan import SubscriptionPlan
from models.subscription import Subscription, SubscriptionStatus
from repositories.subscription_plan_repo import SubscriptionPlanRepository
from repositories.subscriber_repo import SubscriberRepository
from repositories.subscription_repo import SubscriptionRepository
from repositories.session_repo import ParkingSessionRepository
from repositories.card_repo import ParkingCardRepository
from services.card_service import CardService
from services.audit_service import AuditService
from services.shift_service import ShiftService
from services.pricing_service import PricingService
from services.plate_service import PlateService
from services.subscription_service import SubscriptionService
from services.session_service import SessionService
from services.exceptions import SubscriptionDailyLimitReachedError
from schemas.subscriptions import SubscriptionCreate
from utils.time import cairo_now


@pytest.fixture
async def setup_session_services(db_session: AsyncSession):
    op = User(
        full_name="Operator Unit",
        username="op_unit_sess",
        hashed_password="pw",
        role=UserRole.OPERATOR,
        gate_number=1,
    )
    db_session.add(op)
    await db_session.flush()

    audit_svc = AuditService(db_session)
    shift_svc = ShiftService(db_session, audit_svc)
    await shift_svc.open_shift(op.id, gate_number=1, opening_cash_egp=50)

    card_svc = CardService(db_session)
    sub_repo = SubscriberRepository(db_session)
    plan_repo = SubscriptionPlanRepository(db_session)
    subscription_repo = SubscriptionRepository(db_session)
    session_repo = ParkingSessionRepository(db_session)
    pricing_svc = PricingService(db_session)
    plate_svc = PlateService()

    sub_svc = SubscriptionService(
        db=db_session,
        subscription_repo=subscription_repo,
        plan_repo=plan_repo,
        card_service=card_svc,
        audit_service=audit_svc,
    )

    session_service = SessionService(
        db=db_session,
        card_service=card_svc,
        session_repo=session_repo,
        pricing_service=pricing_svc,
        shift_service=shift_svc,
        audit_service=audit_svc,
        plate_service=plate_svc,
        subscription_service=sub_svc,
    )

    return {
        "op": op,
        "session_service": session_service,
        "sub_svc": sub_svc,
        "plan_repo": plan_repo,
        "sub_repo": sub_repo,
        "card_svc": card_svc,
    }


@pytest.mark.asyncio
async def test_open_session_subscribed_sets_flag(db_session: AsyncSession, setup_session_services):
    ctx = setup_session_services
    op = ctx["op"]
    session_service = ctx["session_service"]
    sub_svc = ctx["sub_svc"]
    plan_repo = ctx["plan_repo"]
    sub_repo = ctx["sub_repo"]

    card = ParkingCard(card_code="CARD-SESS-1", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.flush()

    plan = await plan_repo.create(
        label="Plan Sess",
        duration_days=30,
        price_piastres=10000,
        max_entries_per_day=None,
        description=None,
        created_by=op.id,
    )
    subscriber = await sub_repo.create(
        full_name="Sub Unit 1",
        plate_number="س س س 123",
        phone_number=None,
        notes=None,
    )

    sub = await sub_svc.create_subscription(
        SubscriptionCreate(
            subscriber_id=subscriber.id,
            plan_id=plan.id,
            card_id=card.id,
            start_date=cairo_now().date(),
            amount_paid_egp=100.0,
        ),
        admin_id=op.id,
    )

    open_res = await session_service.open_session("CARD-SESS-1", operator_id=op.id)
    assert open_res.is_subscribed is True
    assert open_res.subscription_id == sub.id


@pytest.mark.asyncio
async def test_open_session_not_subscribed_flag_false(db_session: AsyncSession, setup_session_services):
    ctx = setup_session_services
    op = ctx["op"]
    session_service = ctx["session_service"]

    card = ParkingCard(card_code="CARD-SESS-2", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.flush()

    open_res = await session_service.open_session("CARD-SESS-2", operator_id=op.id)
    assert open_res.is_subscribed is False
    assert open_res.subscription_id is None


@pytest.mark.asyncio
async def test_open_session_daily_limit_blocks(db_session: AsyncSession, setup_session_services):
    ctx = setup_session_services
    op = ctx["op"]
    session_service = ctx["session_service"]
    sub_svc = ctx["sub_svc"]
    plan_repo = ctx["plan_repo"]
    sub_repo = ctx["sub_repo"]

    card = ParkingCard(card_code="CARD-SESS-3", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.flush()

    # Plan with max 1 entry per day
    plan = await plan_repo.create(
        label="Plan 1 Entry",
        duration_days=30,
        price_piastres=10000,
        max_entries_per_day=1,
        description=None,
        created_by=op.id,
    )
    subscriber = await sub_repo.create(
        full_name="Sub Unit 2",
        plate_number="س س س 124",
        phone_number=None,
        notes=None,
    )

    sub = await sub_svc.create_subscription(
        SubscriptionCreate(
            subscriber_id=subscriber.id,
            plan_id=plan.id,
            card_id=card.id,
            start_date=cairo_now().date(),
            amount_paid_egp=100.0,
        ),
        admin_id=op.id,
    )

    op_id = op.id
    # First session opens and closes
    open1 = await session_service.open_session("CARD-SESS-3", operator_id=op_id)
    await session_service.close_session(open1.id, exit_operator_id=op_id)

    # Second entry on the same day should raise SubscriptionDailyLimitReachedError
    with pytest.raises(SubscriptionDailyLimitReachedError):
        await session_service.open_session("CARD-SESS-3", operator_id=op_id)


@pytest.mark.asyncio
async def test_close_subscribed_session_zero_charge_and_none_calc(db_session: AsyncSession, setup_session_services):
    ctx = setup_session_services
    op = ctx["op"]
    session_service = ctx["session_service"]
    sub_svc = ctx["sub_svc"]
    plan_repo = ctx["plan_repo"]
    sub_repo = ctx["sub_repo"]

    card = ParkingCard(card_code="CARD-SESS-4", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.flush()

    plan = await plan_repo.create(
        label="Plan Sess Free",
        duration_days=30,
        price_piastres=10000,
        max_entries_per_day=None,
        description=None,
        created_by=op.id,
    )
    subscriber = await sub_repo.create(
        full_name="Sub Unit 3",
        plate_number="س س س 125",
        phone_number=None,
        notes=None,
    )

    await sub_svc.create_subscription(
        SubscriptionCreate(
            subscriber_id=subscriber.id,
            plan_id=plan.id,
            card_id=card.id,
            start_date=cairo_now().date(),
            amount_paid_egp=100.0,
        ),
        admin_id=op.id,
    )

    open_res = await session_service.open_session("CARD-SESS-4", operator_id=op.id)
    closed, calc = await session_service.close_session(open_res.id, exit_operator_id=op.id)

    assert closed.amount_charged == 0
    assert closed.is_paid is True
    assert closed.pricing_rule_id is None
    assert calc is None
