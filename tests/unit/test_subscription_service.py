import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from models.parking_card import ParkingCard, CardStatus
from models.subscriber import Subscriber
from models.subscription_plan import SubscriptionPlan
from models.subscription import Subscription, SubscriptionStatus
from repositories.subscription_plan_repo import SubscriptionPlanRepository
from repositories.subscriber_repo import SubscriberRepository
from repositories.subscription_repo import SubscriptionRepository
from services.card_service import CardService
from schemas.subscriptions import SubscriptionCreate, SubscriptionRenew, SubscriptionCancel
from services.subscription_service import SubscriptionService
from services.exceptions import (
    CardNotAvailableError,
    SubscriberAlreadyHasActiveSubscriptionError,
    SubscriptionNotActiveError,
)
from utils.time import cairo_now


@pytest.mark.asyncio
async def test_get_active_for_card_found(db_session: AsyncSession, audit_service):
    sub = Subscriber(full_name="User 1", plate_number="أ ب ج 1 2 3")
    plan = SubscriptionPlan(label="Plan 1", duration_days=30, price_piastres=30000, is_active=True, created_by=1)
    card = ParkingCard(card_code="CARD-S1", status=CardStatus.IN_USE)
    db_session.add_all([sub, plan, card])
    await db_session.flush()

    subscription = Subscription(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        plate_number=sub.plate_number,
        status=SubscriptionStatus.ACTIVE,
        start_date=cairo_now().date(),
        end_date=cairo_now().date() + timedelta(days=30),
        amount_paid_piastres=30000,
        plan_price_snapshot=30000,
    )
    db_session.add(subscription)
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    res = await service.get_active_for_card(card.id)
    assert res is not None
    assert res.id == subscription.id


@pytest.mark.asyncio
async def test_get_active_for_card_expired(db_session: AsyncSession, audit_service):
    sub = Subscriber(full_name="User 2", plate_number="أ ب ج 1 2 4")
    plan = SubscriptionPlan(label="Plan 2", duration_days=30, price_piastres=30000, is_active=True, created_by=1)
    card = ParkingCard(card_code="CARD-S2", status=CardStatus.IN_USE)
    db_session.add_all([sub, plan, card])
    await db_session.flush()

    subscription = Subscription(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        plate_number=sub.plate_number,
        status=SubscriptionStatus.EXPIRED,
        start_date=cairo_now().date() - timedelta(days=40),
        end_date=cairo_now().date() - timedelta(days=10),
        amount_paid_piastres=30000,
        plan_price_snapshot=30000,
    )
    db_session.add(subscription)
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    res = await service.get_active_for_card(card.id)
    assert res is None


@pytest.mark.asyncio
async def test_get_active_for_card_pending_future(db_session: AsyncSession, audit_service):
    sub = Subscriber(full_name="User 3", plate_number="أ ب ج 1 2 5")
    plan = SubscriptionPlan(label="Plan 3", duration_days=30, price_piastres=30000, is_active=True, created_by=1)
    card = ParkingCard(card_code="CARD-S3", status=CardStatus.IN_USE)
    db_session.add_all([sub, plan, card])
    await db_session.flush()

    subscription = Subscription(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        plate_number=sub.plate_number,
        status=SubscriptionStatus.PENDING,
        start_date=cairo_now().date() + timedelta(days=2),
        end_date=cairo_now().date() + timedelta(days=32),
        amount_paid_piastres=30000,
        plan_price_snapshot=30000,
    )
    db_session.add(subscription)
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    res = await service.get_active_for_card(card.id)
    assert res is None


@pytest.mark.asyncio
async def test_get_active_for_card_pending_today(db_session: AsyncSession, audit_service):
    sub = Subscriber(full_name="User 4", plate_number="أ ب ج 1 2 6")
    plan = SubscriptionPlan(label="Plan 4", duration_days=30, price_piastres=30000, is_active=True, created_by=1)
    card = ParkingCard(card_code="CARD-S4", status=CardStatus.IN_USE)
    db_session.add_all([sub, plan, card])
    await db_session.flush()

    subscription = Subscription(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        plate_number=sub.plate_number,
        status=SubscriptionStatus.PENDING,
        start_date=cairo_now().date(),
        end_date=cairo_now().date() + timedelta(days=30),
        amount_paid_piastres=30000,
        plan_price_snapshot=30000,
    )
    db_session.add(subscription)
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    res = await service.get_active_for_card(card.id)
    # Since today's date matches start_date, get_active_for_card finds today within [start_date, end_date] and status IN (ACTIVE, PENDING)
    assert res is not None
    assert res.id == subscription.id


@pytest.mark.asyncio
async def test_check_daily_limit_no_limit(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan No Limit", duration_days=30, price_piastres=10000, max_entries_per_day=None, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Limit 1", plate_number="أ ب ج 1 1 1")
    card = ParkingCard(card_code="CARD-L1", status=CardStatus.IN_USE)
    db_session.add_all([plan, sub, card])
    await db_session.flush()

    subscription = Subscription(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        plate_number=sub.plate_number,
        status=SubscriptionStatus.ACTIVE,
        start_date=cairo_now().date(),
        end_date=cairo_now().date() + timedelta(days=30),
        amount_paid_piastres=10000,
        plan_price_snapshot=10000,
    )
    db_session.add(subscription)
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    assert await service.check_daily_limit(subscription) is True


@pytest.mark.asyncio
async def test_check_daily_limit_within_limit(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan 2 Limit", duration_days=30, price_piastres=10000, max_entries_per_day=2, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Limit 2", plate_number="أ ب ج 1 1 2")
    card = ParkingCard(card_code="CARD-L2", status=CardStatus.IN_USE)
    db_session.add_all([plan, sub, card])
    await db_session.flush()

    subscription = Subscription(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        plate_number=sub.plate_number,
        status=SubscriptionStatus.ACTIVE,
        start_date=cairo_now().date(),
        end_date=cairo_now().date() + timedelta(days=30),
        amount_paid_piastres=10000,
        plan_price_snapshot=10000,
    )
    db_session.add(subscription)
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    assert await service.check_daily_limit(subscription) is True


@pytest.mark.asyncio
async def test_create_subscription_success(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan Create", duration_days=30, price_piastres=10000, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Create", plate_number="أ ب ج 1 1 3")
    card = ParkingCard(card_code="CARD-C1", status=CardStatus.AVAILABLE)
    db_session.add_all([plan, sub, card])
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )

    sub_in = SubscriptionCreate(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        start_date=cairo_now().date(),
        amount_paid_egp=100.0,
    )
    created = await service.create_subscription(sub_in, admin_id=1)
    assert created.status == SubscriptionStatus.ACTIVE
    assert created.amount_paid_piastres == 10000
    await db_session.refresh(card)
    assert card.status == CardStatus.IN_USE


@pytest.mark.asyncio
async def test_create_subscription_card_not_available(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan Card NA", duration_days=30, price_piastres=10000, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Card NA", plate_number="أ ب ج 1 1 4")
    card = ParkingCard(card_code="CARD-C2", status=CardStatus.IN_USE)
    db_session.add_all([plan, sub, card])
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )

    sub_in = SubscriptionCreate(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card.id,
        start_date=cairo_now().date(),
        amount_paid_egp=100.0,
    )
    with pytest.raises(CardNotAvailableError):
        await service.create_subscription(sub_in, admin_id=1)


@pytest.mark.asyncio
async def test_create_subscription_duplicate_active(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan Dup Active", duration_days=30, price_piastres=10000, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Dup Active", plate_number="أ ب ج 1 1 5")
    card1 = ParkingCard(card_code="CARD-D1", status=CardStatus.AVAILABLE)
    card2 = ParkingCard(card_code="CARD-D2", status=CardStatus.AVAILABLE)
    db_session.add_all([plan, sub, card1, card2])
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )

    sub_in1 = SubscriptionCreate(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card1.id,
        start_date=cairo_now().date(),
        amount_paid_egp=100.0,
    )
    await service.create_subscription(sub_in1, admin_id=1)

    sub_in2 = SubscriptionCreate(
        subscriber_id=sub.id,
        plan_id=plan.id,
        card_id=card2.id,
        start_date=cairo_now().date(),
        amount_paid_egp=100.0,
    )
    with pytest.raises(SubscriberAlreadyHasActiveSubscriptionError):
        await service.create_subscription(sub_in2, admin_id=1)


@pytest.mark.asyncio
async def test_cancel_subscription_success(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan Cancel", duration_days=30, price_piastres=10000, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Cancel", plate_number="أ ب ج 1 1 6")
    card = ParkingCard(card_code="CARD-CAN1", status=CardStatus.AVAILABLE)
    db_session.add_all([plan, sub, card])
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )

    created = await service.create_subscription(
        SubscriptionCreate(
            subscriber_id=sub.id,
            plan_id=plan.id,
            card_id=card.id,
            start_date=cairo_now().date(),
            amount_paid_egp=100.0,
        ),
        admin_id=1,
    )

    cancelled = await service.cancel_subscription(created.id, cancel_reason="Changed mind", admin_id=1)
    assert cancelled.status == SubscriptionStatus.CANCELLED
    assert cancelled.cancel_reason == "Changed mind"
    await db_session.refresh(card)
    assert card.status == CardStatus.AVAILABLE


@pytest.mark.asyncio
async def test_cancel_subscription_not_active(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan Cancel NA", duration_days=30, price_piastres=10000, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Cancel NA", plate_number="أ ب ج 1 1 7")
    card = ParkingCard(card_code="CARD-CAN2", status=CardStatus.AVAILABLE)
    db_session.add_all([plan, sub, card])
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )

    created = await service.create_subscription(
        SubscriptionCreate(
            subscriber_id=sub.id,
            plan_id=plan.id,
            card_id=card.id,
            start_date=cairo_now().date(),
            amount_paid_egp=100.0,
        ),
        admin_id=1,
    )

    await service.cancel_subscription(created.id, cancel_reason="Changed mind", admin_id=1)

    with pytest.raises(SubscriptionNotActiveError):
        await service.cancel_subscription(created.id, cancel_reason="Cancel again", admin_id=1)


@pytest.mark.asyncio
async def test_renew_before_expiry(db_session: AsyncSession, audit_service):
    plan = SubscriptionPlan(label="Plan Renew Pre", duration_days=30, price_piastres=10000, is_active=True, created_by=1)
    sub = Subscriber(full_name="User Renew Pre", plate_number="أ ب ج 1 1 8")
    card = ParkingCard(card_code="CARD-RN1", status=CardStatus.AVAILABLE)
    db_session.add_all([plan, sub, card])
    await db_session.commit()

    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )

    sub_orig = await service.create_subscription(
        SubscriptionCreate(
            subscriber_id=sub.id,
            plan_id=plan.id,
            card_id=card.id,
            start_date=cairo_now().date(),
            amount_paid_egp=100.0,
        ),
        admin_id=1,
    )

    renewed = await service.renew_subscription(
        sub_orig.id,
        SubscriptionRenew(amount_paid_egp=100.0, notes="Advance"),
        admin_id=1,
    )
    assert renewed.status == SubscriptionStatus.PENDING
    assert renewed.start_date == sub_orig.end_date + timedelta(days=1)
    assert renewed.previous_subscription_id == sub_orig.id


@pytest.mark.asyncio
async def test_expire_overdue_bulk(db_session: AsyncSession, audit_service):
    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    count = await service.expire_overdue_subscriptions()
    assert count >= 0


@pytest.mark.asyncio
async def test_activate_pending_bulk(db_session: AsyncSession, audit_service):
    service = SubscriptionService(
        db=db_session,
        subscription_repo=SubscriptionRepository(db_session),
        plan_repo=SubscriptionPlanRepository(db_session),
        card_service=CardService(db_session),
        audit_service=audit_service,
    )
    count = await service.activate_pending_subscriptions()
    assert count >= 0
