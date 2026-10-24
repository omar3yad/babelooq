import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User, UserRole
from models.parking_card import ParkingCard, CardStatus
from models.subscription import SubscriptionStatus
from repositories.subscription_plan_repo import SubscriptionPlanRepository
from repositories.subscriber_repo import SubscriberRepository
from repositories.subscription_repo import SubscriptionRepository
from repositories.session_repo import ParkingSessionRepository
from schemas.subscriptions import (
    PlanCreate,
    PlanUpdate,
    SubscriberCreate,
    SubscriberUpdate,
    SubscriptionCreate,
    SubscriptionRenew,
)
from services.audit_service import AuditService
from services.card_service import CardService
from services.plate_service import PlateService
from services.pricing_service import PricingService
from services.shift_service import ShiftService
from services.session_service import SessionService
from services.subscription_plan_service import SubscriptionPlanService
from services.subscriber_service import SubscriberService
from services.subscription_service import SubscriptionService
from services.report_service import ReportService
from services.exceptions import (
    PlanNotFoundError,
    PlanLabelAlreadyExistsError,
    SubscriberPlateAlreadyExistsError,
)
from utils.time import cairo_now


@pytest.mark.asyncio
async def test_plan_service_crud(db_session: AsyncSession):
    user = User(full_name="Admin", username="admin_p", hashed_password="pw", role=UserRole.ADMIN)
    db_session.add(user)
    await db_session.flush()

    plan_repo = SubscriptionPlanRepository(db_session)
    audit_svc = AuditService(db_session)
    service = SubscriptionPlanService(db_session, plan_repo, audit_svc)

    # 1. Create plan
    data = PlanCreate(
        label="Monthly VIP",
        duration_days=30,
        price_egp=150.0,
        max_entries_per_day=2,
        description="VIP plan",
    )
    plan = await service.create_plan(data, admin_id=user.id)
    assert plan.id is not None
    assert plan.price_piastres == 15000
    assert plan.is_active is True

    # Duplicate label raises error
    with pytest.raises(PlanLabelAlreadyExistsError):
        await service.create_plan(data, admin_id=user.id)

    # 2. Deactivate plan
    deactivated = await service.deactivate_plan(plan.id, admin_id=user.id)
    assert deactivated.is_active is False

    with pytest.raises(PlanNotFoundError):
        await service.deactivate_plan(99999, admin_id=user.id)

    # 3. Update plan
    updated = await service.update_plan(
        plan.id,
        PlanUpdate(label="Monthly Super VIP", price_egp=200.0, is_active=True),
        admin_id=user.id,
    )
    assert updated.label == "Monthly Super VIP"
    assert updated.price_piastres == 20000
    assert updated.is_active is True


@pytest.mark.asyncio
async def test_subscriber_service_crud_and_normalization(db_session: AsyncSession):
    user = User(full_name="Admin", username="admin_sub_s", hashed_password="pw", role=UserRole.ADMIN)
    db_session.add(user)
    await db_session.flush()

    sub_repo = SubscriberRepository(db_session)
    plate_svc = PlateService()
    audit_svc = AuditService(db_session)
    service = SubscriberService(db_session, sub_repo, plate_svc, audit_svc)

    # 1. Create with Eastern numerals (should normalize to Western)
    data = SubscriberCreate(
        full_name="Hassan Ahmed",
        plate_number="ن ي ش ١٥٩",
        phone_number="01099998888",
    )
    subscriber = await service.create_subscriber(data, admin_id=user.id)
    assert subscriber.plate_number == "ن ي ش 159"

    # Duplicate plate raises error
    with pytest.raises(SubscriberPlateAlreadyExistsError):
        await service.create_subscriber(data, admin_id=user.id)

    # 2. Update subscriber
    updated = await service.update_subscriber(
        subscriber.id,
        SubscriberUpdate(full_name="Hassan A. Mahmoud"),
        admin_id=user.id,
    )
    assert updated.full_name == "Hassan A. Mahmoud"


@pytest.mark.asyncio
async def test_subscription_service_full_flow(db_session: AsyncSession):
    user = User(full_name="Admin", username="admin_flow", hashed_password="pw", role=UserRole.ADMIN)
    card = ParkingCard(card_code="CARD-FLOW-1", status=CardStatus.AVAILABLE)
    db_session.add_all([user, card])
    await db_session.flush()

    plan_repo = SubscriptionPlanRepository(db_session)
    sub_repo = SubscriberRepository(db_session)
    subscription_repo = SubscriptionRepository(db_session)
    card_svc = CardService(db_session)
    audit_svc = AuditService(db_session)

    plan = await plan_repo.create(
        label="Monthly Flow",
        duration_days=30,
        price_piastres=15000,
        max_entries_per_day=1,
        description=None,
        created_by=user.id,
    )
    subscriber = await sub_repo.create(
        full_name="Subscriber Flow",
        plate_number="أ ب ج 777",
        phone_number=None,
        notes=None,
    )

    sub_service = SubscriptionService(
        db=db_session,
        subscription_repo=subscription_repo,
        plan_repo=plan_repo,
        card_service=card_svc,
        audit_service=audit_svc,
    )

    today = cairo_now().date()

    # 1. Create subscription
    sub_create = SubscriptionCreate(
        subscriber_id=subscriber.id,
        plan_id=plan.id,
        card_id=card.id,
        start_date=today,
        amount_paid_egp=150.0,
    )
    subscription = await sub_service.create_subscription(sub_create, admin_id=user.id)
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.amount_paid_piastres == 15000

    await db_session.refresh(card)
    assert card.status == CardStatus.IN_USE

    # 2. Check active for card
    active = await sub_service.get_active_for_card(card.id)
    assert active is not None
    assert active.id == subscription.id

    # 3. Renew subscription before expiry (creates PENDING continuation)
    renew_req = SubscriptionRenew(amount_paid_egp=150.0, notes="Advance renewal")
    renewed = await sub_service.renew_subscription(subscription.id, renew_req, admin_id=user.id)
    assert renewed.status == SubscriptionStatus.PENDING
    assert renewed.start_date == subscription.end_date + timedelta(days=1)
    assert renewed.previous_subscription_id == subscription.id

    # 4. Cancel subscription (frees card)
    cancelled = await sub_service.cancel_subscription(
        subscription.id, cancel_reason="Driver relocation", admin_id=user.id
    )
    assert cancelled.status == SubscriptionStatus.CANCELLED
    await db_session.refresh(card)
    assert card.status == CardStatus.AVAILABLE


@pytest.mark.asyncio
async def test_session_service_subscribed_entry_exit(db_session: AsyncSession):
    # Setup Operator, Shift, Card, Plan, Subscriber, Subscription
    op = User(
        full_name="Operator Entry",
        username="op_entry",
        hashed_password="pw",
        role=UserRole.OPERATOR,
        gate_number=1,
    )
    db_session.add(op)
    await db_session.flush()

    card = ParkingCard(card_code="CARD-SUB-1", status=CardStatus.AVAILABLE)
    db_session.add(card)
    await db_session.flush()

    audit_svc = AuditService(db_session)
    shift_svc = ShiftService(db_session, audit_svc)
    await shift_svc.open_shift(op.id, gate_number=1, opening_cash_egp=100)

    plan_repo = SubscriptionPlanRepository(db_session)
    plan = await plan_repo.create(
        label="Sub Plan", duration_days=30, price_piastres=10000, max_entries_per_day=None, description=None, created_by=op.id
    )
    sub_repo = SubscriberRepository(db_session)
    subscriber = await sub_repo.create(full_name="Sub User", plate_number="م م م 123", phone_number=None, notes=None)

    subscription_repo = SubscriptionRepository(db_session)
    card_svc = CardService(db_session)
    sub_svc = SubscriptionService(db_session, subscription_repo, plan_repo, card_svc, audit_svc)

    today = cairo_now().date()
    sub = await sub_svc.create_subscription(
        SubscriptionCreate(
            subscriber_id=subscriber.id,
            plan_id=plan.id,
            card_id=card.id,
            start_date=today,
            amount_paid_egp=100.0,
        ),
        admin_id=op.id,
    )

    session_repo = ParkingSessionRepository(db_session)
    pricing_svc = PricingService(db_session)
    plate_svc = PlateService()

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

    # 1. Open session with subscribed card
    open_res = await session_service.open_session("CARD-SUB-1", operator_id=op.id)
    assert open_res.is_subscribed is True
    assert open_res.subscription_id == sub.id

    # 2. Close session with subscribed card (0 charge, no pricing rule)
    closed_session, calc = await session_service.close_session(open_res.id, exit_operator_id=op.id)
    assert closed_session.amount_charged == 0
    assert closed_session.is_paid is True
    assert closed_session.pricing_rule_id is None
    assert calc is None


@pytest.mark.asyncio
async def test_report_service_subscription_revenue(db_session: AsyncSession):
    user = User(full_name="Admin", username="admin_rep", hashed_password="pw", role=UserRole.ADMIN)
    card = ParkingCard(card_code="CARD-REP-1", status=CardStatus.AVAILABLE)
    db_session.add_all([user, card])
    await db_session.flush()

    plan_repo = SubscriptionPlanRepository(db_session)
    plan = await plan_repo.create(
        label="Plan Gold", duration_days=30, price_piastres=25000, max_entries_per_day=None, description=None, created_by=user.id
    )
    sub_repo = SubscriberRepository(db_session)
    subscriber = await sub_repo.create(full_name="Sub Rep", plate_number="ط ط ط 999", phone_number=None, notes=None)

    subscription_repo = SubscriptionRepository(db_session)
    today = cairo_now().date()
    await subscription_repo.create(
        subscriber_id=subscriber.id,
        plan_id=plan.id,
        card_id=card.id,
        plate_number="ط ط ط 999",
        start_date=today,
        end_date=today + timedelta(days=30),
        status=SubscriptionStatus.ACTIVE,
        amount_paid_piastres=25000,
        plan_price_snapshot=25000,
        paid_at=datetime.utcnow(),
        collected_by=user.id,
    )

    report_svc = ReportService(db_session)
    summary = await report_svc.get_subscription_revenue_summary(
        start_date=today - timedelta(days=1),
        end_date=today + timedelta(days=1),
        plan_id=None,
        subscription_repo=subscription_repo,
    )
    assert summary.total_subscriptions == 1
    assert summary.total_revenue_piastres == 25000
    assert len(summary.by_plan) == 1
    assert summary.by_plan[0].plan_label == "Plan Gold"
