from sqlalchemy.ext.asyncio import AsyncSession

from models.subscription_plan import SubscriptionPlan
from repositories.subscription_plan_repo import SubscriptionPlanRepository
from schemas.subscriptions import PlanCreate, PlanUpdate
from services.audit_service import AuditService
from services.exceptions import PlanNotFoundError, PlanLabelAlreadyExistsError


class SubscriptionPlanService:
    def __init__(
        self,
        db: AsyncSession,
        plan_repo: SubscriptionPlanRepository,
        audit_service: AuditService,
    ):
        self.db = db
        self.plan_repo = plan_repo
        self.audit_service = audit_service

    async def create_plan(
        self, data: PlanCreate, admin_id: int
    ) -> SubscriptionPlan:
        """Creates a new subscription plan with uniqueness check on label."""
        existing = await self.plan_repo.get_by_label(data.label)
        if existing is not None:
            raise PlanLabelAlreadyExistsError(f"Plan with label '{data.label}' already exists")

        plan = await self.plan_repo.create(
            label=data.label,
            duration_days=data.duration_days,
            price_piastres=data.price_piastres,
            max_entries_per_day=data.max_entries_per_day,
            description=data.description,
            created_by=admin_id,
        )
        await self.db.commit()
        await self.db.refresh(plan)

        await self.audit_service.log(
            actor_id=admin_id,
            action="PLAN_CREATED",
            entity_type="subscription_plan",
            entity_id=plan.id,
            before=None,
            after={
                "label": plan.label,
                "duration_days": plan.duration_days,
                "price_piastres": plan.price_piastres,
            },
        )
        return plan

    async def deactivate_plan(
        self, plan_id: int, admin_id: int
    ) -> SubscriptionPlan:
        """Deactivates a subscription plan without affecting existing subscriptions."""
        plan = await self.plan_repo.get_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError("Plan not found")

        before_state = {"is_active": plan.is_active}
        await self.plan_repo.update_fields(plan, is_active=False)
        await self.db.commit()
        await self.db.refresh(plan)

        await self.audit_service.log(
            actor_id=admin_id,
            action="PLAN_DEACTIVATED",
            entity_type="subscription_plan",
            entity_id=plan.id,
            before=before_state,
            after={"is_active": False},
        )
        return plan

    async def update_plan(
        self, plan_id: int, data: PlanUpdate, admin_id: int
    ) -> SubscriptionPlan:
        """Updates plan fields (label, price, description, max_entries_per_day, is_active)."""
        plan = await self.plan_repo.get_by_id(plan_id)
        if plan is None:
            raise PlanNotFoundError("Plan not found")

        before_state = {
            "label": plan.label,
            "duration_days": plan.duration_days,
            "price_piastres": plan.price_piastres,
            "description": plan.description,
            "max_entries_per_day": plan.max_entries_per_day,
            "is_active": plan.is_active,
        }

        updates: dict = {}
        if data.label is not None:
            # Check label uniqueness
            existing = await self.plan_repo.get_by_label(data.label)
            if existing is not None and existing.id != plan_id:
                raise PlanLabelAlreadyExistsError(f"Plan with label '{data.label}' already exists")
            updates["label"] = data.label

        if data.price_egp is not None:
            updates["price_piastres"] = round(data.price_egp * 100)

        if data.description is not None:
            updates["description"] = data.description

        if data.max_entries_per_day is not None:
            updates["max_entries_per_day"] = data.max_entries_per_day

        if data.is_active is not None:
            updates["is_active"] = data.is_active

        if updates:
            await self.plan_repo.update_fields(plan, **updates)
            await self.db.commit()
            await self.db.refresh(plan)

        after_state = {
            "label": plan.label,
            "duration_days": plan.duration_days,
            "price_piastres": plan.price_piastres,
            "description": plan.description,
            "max_entries_per_day": plan.max_entries_per_day,
            "is_active": plan.is_active,
        }

        await self.audit_service.log(
            actor_id=admin_id,
            action="PLAN_UPDATED",
            entity_type="subscription_plan",
            entity_id=plan.id,
            before=before_state,
            after=after_state,
        )
        return plan


__all__ = ["SubscriptionPlanService"]
