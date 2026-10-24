import asyncio
from datetime import date, datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.subscription import Subscription, SubscriptionStatus
from models.subscriber import Subscriber
from models.parking_card import ParkingCard, CardStatus
from models.subscription_plan import SubscriptionPlan
from repositories.subscription_plan_repo import SubscriptionPlanRepository
from repositories.subscription_repo import SubscriptionRepository
from schemas.subscriptions import (
    SubscriptionCreate,
    SubscriptionRenew,
    SubscriptionDashboardStats,
)
from services.audit_service import AuditService
from services.card_service import CardService
from services.exceptions import (
    PlanNotFoundError,
    PlanNotActiveError,
    CardNotFoundError,
    CardNotAvailableError,
    SubscriberNotFoundError,
    SubscriptionNotFoundError,
    SubscriptionNotActiveError,
    SubscriberAlreadyHasActiveSubscriptionError,
)
from utils.time import cairo_now, cairo_today_start


class SubscriptionService:
    def __init__(
        self,
        db: AsyncSession,
        subscription_repo: SubscriptionRepository,
        plan_repo: SubscriptionPlanRepository,
        card_service: CardService,
        audit_service: AuditService,
    ):
        self.db = db
        self.subscription_repo = subscription_repo
        self.plan_repo = plan_repo
        self.card_service = card_service
        self.audit_service = audit_service

    async def get_active_for_card(self, card_id: int) -> Subscription | None:
        """Silently fetches active subscription for a card without raising exceptions."""
        try:
            today = cairo_now().date()
            return await self.subscription_repo.get_active_for_card(card_id, today)
        except Exception:
            return None

    async def check_daily_limit(self, subscription: Subscription) -> bool:
        """Returns True if the vehicle has not yet exceeded max daily entries for its plan."""
        plan = await self.plan_repo.get_by_id(subscription.plan_id)
        if not plan or plan.max_entries_per_day is None:
            return True

        day_start_utc = cairo_today_start()
        day_end_utc = day_start_utc + timedelta(days=1)
        count = await self.subscription_repo.count_daily_entries(
            subscription.id, day_start_utc, day_end_utc
        )
        return count < plan.max_entries_per_day

    async def create_subscription(
        self, data: SubscriptionCreate, admin_id: int
    ) -> Subscription:
        """Creates and activates a new subscription, linking a card to a subscriber."""
        plan = None
        if data.plan_id:
            plan = await self.plan_repo.get_by_id(data.plan_id)
            if plan is None:
                raise PlanNotFoundError("Subscription plan not found")
            if not plan.is_active:
                raise PlanNotActiveError("Subscription plan is not active")
        else:
            # Look for existing custom plan or create one
            custom_res = await self.db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.label.ilike("%اشتراك مخصص%")).limit(1)
            )
            plan = custom_res.scalars().first()
            if not plan:
                plan = SubscriptionPlan(
                    label="اشتراك مخصص (سعر حر)",
                    duration_days=data.duration_days or 30,
                    price_piastres=data.amount_paid_piastres,
                    is_active=True,
                    created_by=admin_id,
                )
                self.db.add(plan)
                await self.db.flush()

        # Fetch card by card_code or card_id
        card = None
        if data.card_code:
            card_code_clean = str(data.card_code).strip()
            result = await self.db.execute(
                select(ParkingCard).where(ParkingCard.card_code == card_code_clean).limit(1)
            )
            card = result.scalars().first()
        elif data.card_id:
            result = await self.db.execute(
                select(ParkingCard).where(ParkingCard.id == data.card_id).limit(1)
            )
            card = result.scalars().first()
        else:
            raise CardNotFoundError("يجب إدخال كود الكرت")

        if card is None:
            raise CardNotFoundError(f"الكرت رقم '{data.card_code or data.card_id}' غير موجود بالنظام")
        if card.status != CardStatus.AVAILABLE:
            raise CardNotAvailableError(f"الكرت رقم '{card.card_code}' غير متاح أو مستخدم بالفعل")

        # Check subscriber existence
        sub_res = await self.db.execute(
            select(Subscriber).where(Subscriber.id == data.subscriber_id).limit(1)
        )
        subscriber = sub_res.scalars().first()
        if subscriber is None:
            raise SubscriberNotFoundError("المشترك غير موجود")

        # Check active subscription uniqueness
        existing_sub = await self.subscription_repo.get_active_for_subscriber(data.subscriber_id)
        if existing_sub is not None:
            raise SubscriberAlreadyHasActiveSubscriptionError(
                "المشترك لديه بالفعل اشتراك نشط أو معلق"
            )

        today = cairo_now().date()
        if data.end_date:
            end_date = data.end_date
        else:
            import calendar
            last_day_num = calendar.monthrange(data.start_date.year, data.start_date.month)[1]
            end_date = date(data.start_date.year, data.start_date.month, last_day_num)

        status = SubscriptionStatus.ACTIVE if data.start_date <= today else SubscriptionStatus.PENDING

        subscription = await self.subscription_repo.create(
            subscriber_id=data.subscriber_id,
            plan_id=plan.id,
            card_id=card.id,
            plate_number=subscriber.plate_number,
            start_date=data.start_date,
            end_date=end_date,
            status=status,
            amount_paid_piastres=data.amount_paid_piastres,
            plan_price_snapshot=data.amount_paid_piastres if not data.plan_id else plan.price_piastres,
            paid_at=datetime.utcnow(),
            collected_by=admin_id,
            renewal_count=0,
            previous_subscription_id=None,
            notes=data.notes,
        )

        if status == SubscriptionStatus.ACTIVE and self.card_service:
            await self.card_service.set_status(card, CardStatus.IN_USE)

        await self.db.commit()
        await self.db.refresh(subscription)

        if self.audit_service:
            await self.audit_service.log(
                actor_id=admin_id,
                action="SUBSCRIPTION_CREATED",
                entity_type="subscription",
                entity_id=subscription.id,
                before=None,
                after={
                    "subscriber_id": subscription.subscriber_id,
                    "plan_id": subscription.plan_id,
                    "card_id": subscription.card_id,
                    "card_code": card.card_code,
                    "end_date": subscription.end_date.isoformat(),
                    "amount_paid_piastres": subscription.amount_paid_piastres,
                },
            )

        return subscription

    async def renew_subscription(
        self, subscription_id: int, data: SubscriptionRenew, admin_id: int
    ) -> Subscription:
        """Renews an existing subscription, creating a new continuation record."""
        old_sub = await self.subscription_repo.get_by_id(subscription_id)
        if old_sub is None:
            raise SubscriptionNotFoundError("Subscription not found")
        if old_sub.status != SubscriptionStatus.ACTIVE:
            raise SubscriptionNotActiveError("Only ACTIVE subscriptions can be renewed")

        plan_id = data.plan_id if data.plan_id is not None else old_sub.plan_id
        plan = await self.plan_repo.get_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError("Subscription plan not found")
        if not plan.is_active:
            raise PlanNotActiveError("Subscription plan is not active")

        today = cairo_now().date()
        if data.start_date:
            new_start = data.start_date
        elif old_sub.end_date >= today:
            new_start = old_sub.end_date + timedelta(days=1)
        else:
            new_start = today

        if data.end_date:
            new_end = data.end_date
        else:
            import calendar
            last_day_num = calendar.monthrange(new_start.year, new_start.month)[1]
            new_end = date(new_start.year, new_start.month, last_day_num)

        new_status = SubscriptionStatus.ACTIVE if new_start <= today else SubscriptionStatus.PENDING


        new_sub = await self.subscription_repo.create(
            subscriber_id=old_sub.subscriber_id,
            plan_id=plan.id,
            card_id=old_sub.card_id,
            plate_number=old_sub.plate_number,
            start_date=new_start,
            end_date=new_end,
            status=new_status,
            amount_paid_piastres=data.amount_paid_piastres,
            plan_price_snapshot=plan.price_piastres,
            paid_at=datetime.utcnow(),
            collected_by=admin_id,
            renewal_count=old_sub.renewal_count + 1,
            previous_subscription_id=old_sub.id,
            notes=data.notes,
        )

        if new_status == SubscriptionStatus.ACTIVE:
            await self.subscription_repo.update_fields(
                old_sub,
                status=SubscriptionStatus.EXPIRED,
                ended_at=datetime.utcnow(),
            )

        await self.db.commit()
        await self.db.refresh(new_sub)

        if self.audit_service:
            await self.audit_service.log(
                actor_id=admin_id,
                action="SUBSCRIPTION_RENEWED",
                entity_type="subscription",
                entity_id=new_sub.id,
                before={"old_id": old_sub.id},
                after={"old_id": old_sub.id, "new_id": new_sub.id},
            )
        return new_sub

    async def cancel_subscription(
        self,
        subscription_id: int,
        cancel_reason: str | None,
        admin_id: int,
    ) -> Subscription:
        """Cancels an active or pending subscription and frees the card."""
        subscription = await self.subscription_repo.get_by_id(subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError("Subscription not found")
        if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING):
            raise SubscriptionNotActiveError("Subscription is not active or pending")

        result = await self.db.execute(
            select(ParkingCard).where(ParkingCard.id == subscription.card_id).limit(1)
        )
        card = result.scalars().first()

        now = datetime.utcnow()
        await self.subscription_repo.update_fields(
            subscription,
            status=SubscriptionStatus.CANCELLED,
            ended_at=now,
            cancel_reason=cancel_reason,
        )

        if card and self.card_service:
            await self.card_service.set_status(card, CardStatus.AVAILABLE)

        await self.db.commit()
        await self.db.refresh(subscription)

        if self.audit_service:
            await self.audit_service.log(
                actor_id=admin_id,
                action="SUBSCRIPTION_CANCELLED",
                entity_type="subscription",
                entity_id=subscription.id,
                before={"status": "ACTIVE"},
                after={"status": "CANCELLED", "cancel_reason": cancel_reason},
            )
        return subscription

    async def expire_overdue_subscriptions(self) -> int:
        """Marks active subscriptions past their end date as EXPIRED and frees cards."""
        today = cairo_now().date()
        count = await self.subscription_repo.bulk_expire_overdue(today)
        await self.db.commit()
        return count

    async def activate_pending_subscriptions(self) -> int:
        """Activates pending subscriptions whose start date has arrived."""
        today = cairo_now().date()
        count = await self.subscription_repo.bulk_activate_pending(today)
        await self.db.commit()
        return count

    async def get_dashboard_stats(self) -> SubscriptionDashboardStats:
        """Returns concurrent dashboard counts for active, expiring, and unrenewed subscriptions."""
        today = cairo_now().date()
        threshold = today + timedelta(days=7)

        async def get_active_count():
            try:
                res = await self.db.execute(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.status == SubscriptionStatus.ACTIVE
                    )
                )
                return res.scalar_one()
            except Exception:
                return 0

        async def get_expiring_count():
            try:
                subs = await self.subscription_repo.get_expiring_soon(threshold)
                return len(subs)
            except Exception:
                return 0

        async def get_expired_unrenewed_count():
            try:
                # Expired subscriptions that have not been renewed
                subquery = select(Subscription.previous_subscription_id).where(
                    Subscription.previous_subscription_id.is_not(None)
                )
                res = await self.db.execute(
                    select(func.count()).select_from(Subscription).where(
                        Subscription.status == SubscriptionStatus.EXPIRED,
                        Subscription.id.not_in(subquery),
                    )
                )
                return res.scalar_one()
            except Exception:
                return 0

        async def get_total_subscribers():
            try:
                res = await self.db.execute(select(func.count()).select_from(Subscriber))
                return res.scalar_one()
            except Exception:
                return 0

        active_cnt, expiring_cnt, unrenewed_cnt, total_subs = await asyncio.gather(
            get_active_count(),
            get_expiring_count(),
            get_expired_unrenewed_count(),
            get_total_subscribers(),
        )

        return SubscriptionDashboardStats(
            active_subscriptions_count=active_cnt,
            expiring_soon_count=expiring_cnt,
            expired_unrenewed_count=unrenewed_cnt,
            total_subscribers=total_subs,
        )

    async def delete_subscription(self, subscription_id: int, admin_id: int) -> None:
        """Deletes a subscription and frees any linked card back to AVAILABLE status."""
        sub = await self.subscription_repo.get_by_id(subscription_id)
        if sub is None:
            raise SubscriptionNotFoundError("الاشتراك غير موجود")

        # Free card if assigned
        if sub.card_id:
            card_res = await self.db.execute(
                select(ParkingCard).where(ParkingCard.id == sub.card_id).limit(1)
            )
            card = card_res.scalars().first()
            if card:
                card.status = CardStatus.AVAILABLE

        before_state = {
            "subscriber_id": sub.subscriber_id,
            "card_id": sub.card_id,
            "status": sub.status.value if hasattr(sub.status, "value") else str(sub.status),
            "start_date": str(sub.start_date),
            "end_date": str(sub.end_date),
        }

        await self.db.delete(sub)
        await self.db.commit()

        if self.audit_service:
            await self.audit_service.log(
                actor_id=admin_id,
                action="SUBSCRIPTION_DELETED",
                entity_type="subscription",
                entity_id=subscription_id,
                before=before_state,
                after=None,
            )


__all__ = ["SubscriptionService"]

