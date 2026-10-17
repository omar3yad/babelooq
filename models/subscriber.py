from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text
from database import Base
from models.mixins import TimestampMixin


class Subscriber(Base, TimestampMixin):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    card_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = ["Subscriber"]
