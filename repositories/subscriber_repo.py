from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.subscriber import Subscriber


class SubscriberRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, subscriber_id: int) -> Subscriber | None:
        """Fetches a subscriber by ID."""
        result = await self.db.execute(
            select(Subscriber).where(Subscriber.id == subscriber_id).limit(1)
        )
        return result.scalars().first()

    async def get_by_plate(self, plate_normalized: str) -> Subscriber | None:
        """Fetches a subscriber by normalized plate number."""
        result = await self.db.execute(
            select(Subscriber).where(Subscriber.plate_number == plate_normalized).limit(1)
        )
        return result.scalars().first()

    async def get_by_card_code(self, card_code: str) -> Subscriber | None:
        """Fetches a subscriber by card code."""
        result = await self.db.execute(
            select(Subscriber).where(Subscriber.card_code == card_code).limit(1)
        )
        return result.scalars().first()

    async def create(
        self,
        full_name: str,
        plate_number: str,
        phone_number: str | None = None,
        notes: str | None = None,
        company_name: str | None = None,
        card_code: str | None = None,
    ) -> Subscriber:
        """Creates a new subscriber and flushes."""
        subscriber = Subscriber(
            full_name=full_name,
            plate_number=plate_number,
            phone_number=phone_number,
            notes=notes,
            company_name=company_name,
            card_code=card_code,
        )
        self.db.add(subscriber)
        await self.db.flush()
        return subscriber

    async def update_fields(
        self, subscriber: Subscriber, **fields
    ) -> Subscriber:
        """Updates fields on a subscriber and flushes."""
        for key, value in fields.items():
            setattr(subscriber, key, value)
        await self.db.flush()
        return subscriber

    async def get_filtered(
        self,
        search: str | None = None,
        plan_id: int | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Subscriber], int]:
        """Returns paginated subscribers with optional search filter and total count."""
        query = select(Subscriber)
        count_query = select(func.count()).select_from(Subscriber)

        if search:
            search_pattern = f"%{search}%"
            search_filter = or_(
                Subscriber.full_name.ilike(search_pattern),
                Subscriber.plate_number.ilike(search_pattern),
                Subscriber.company_name.ilike(search_pattern),
                Subscriber.card_code.ilike(search_pattern),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar_one()

        offset_val = (page - 1) * size
        query = query.order_by(Subscriber.created_at.desc()).offset(offset_val).limit(size)
        result = await self.db.execute(query)
        subscribers = list(result.scalars().all())

        return subscribers, total_count


__all__ = ["SubscriberRepository"]

