from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.parking_card import ParkingCard, CardStatus


class ParkingCardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, card_id: int) -> ParkingCard | None:
        """Fetches a parking card by its ID, returning None if not found."""
        result = await self.db.execute(
            select(ParkingCard).where(ParkingCard.id == card_id).limit(1)
        )
        return result.scalars().first()

    async def get_by_code(self, card_code: str) -> ParkingCard | None:
        """Fetches a parking card by its code, returning None if not found."""
        result = await self.db.execute(
            select(ParkingCard).where(ParkingCard.card_code == card_code).limit(1)
        )
        return result.scalars().first()

    async def create(self, card_code: str) -> ParkingCard:
        """Creates a single new card in the AVAILABLE status, flushing changes."""
        card = ParkingCard(card_code=card_code, status=CardStatus.AVAILABLE)
        self.db.add(card)
        await self.db.flush()
        return card

    async def bulk_create(self, card_codes: list[str]) -> list[ParkingCard]:
        """Bulk creates multiple cards in the AVAILABLE status, flushing once."""
        cards = [
            ParkingCard(card_code=code, status=CardStatus.AVAILABLE)
            for code in card_codes
        ]
        self.db.add_all(cards)
        await self.db.flush()
        return cards

    async def get_all(
        self,
        status: CardStatus | None = None,
        search: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ParkingCard], int]:
        """Returns a paginated list of cards (with optional status & search filter) and the total count."""
        query = select(ParkingCard)
        count_query = select(func.count()).select_from(ParkingCard)

        if status is not None:
            query = query.where(ParkingCard.status == status)
            count_query = count_query.where(ParkingCard.status == status)

        if search:
            search_clean = f"%{search.strip().upper()}%"
            query = query.where(ParkingCard.card_code.ilike(search_clean))
            count_query = count_query.where(ParkingCard.card_code.ilike(search_clean))

        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar_one()

        offset_val = (page - 1) * size
        query = query.order_by(ParkingCard.id.desc()).offset(offset_val).limit(size)
        result = await self.db.execute(query)
        cards = list(result.scalars().all())

        return cards, total_count

    async def get_counts(self) -> dict[str, int]:
        """Returns total counts grouped by status."""
        result = await self.db.execute(
            select(ParkingCard.status, func.count(ParkingCard.id)).group_by(ParkingCard.status)
        )
        counts = {status.value: count for status, count in result.all()}
        total = sum(counts.values())
        return {
            "total": total,
            "available": counts.get(CardStatus.AVAILABLE.value, 0),
            "in_use": counts.get(CardStatus.IN_USE.value, 0),
            "lost": counts.get(CardStatus.LOST.value, 0),
            "damaged": counts.get(CardStatus.DAMAGED.value, 0),
        }

    async def get_existing_codes(self, codes: list[str]) -> list[str]:
        """Queries for existing card codes in the given list of codes."""
        if not codes:
            return []
        result = await self.db.execute(
            select(ParkingCard.card_code).where(ParkingCard.card_code.in_(codes))
        )
        return list(result.scalars().all())


__all__ = ["ParkingCardRepository"]

