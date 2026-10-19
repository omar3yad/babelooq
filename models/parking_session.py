import enum
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, SmallInteger, ForeignKey, Enum, Text, Index, Float, text
from database import Base
from models.mixins import TimestampMixin

class SessionStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    LOST_CARD = "LOST_CARD"

class PaymentMethod(enum.Enum):
    CASH = "CASH"
    cash = "cash"

class PlateCaptureStatus(str, enum.Enum):
    """Lifecycle of the edge camera capture attached to an entry session.

    Stored as a plain string column so adding states never needs a DB enum migration.
    """
    PENDING = "PENDING"      # trigger dispatched, waiting for the edge PC
    SUCCESS = "SUCCESS"      # plate read and stored
    NO_PLATE = "NO_PLATE"    # image captured but no plate recognised
    FAILED = "FAILED"        # edge reported an error (camera/model)
    TIMEOUT = "TIMEOUT"      # no result before the deadline
    OFFLINE = "OFFLINE"      # no edge PC connected for this gate

    @property
    def is_terminal(self) -> bool:
        return self is not PlateCaptureStatus.PENDING


class ParkingSession(Base, TimestampMixin):
    __tablename__ = "parking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("parking_cards.id"), nullable=False, index=True)
    card_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), nullable=False, server_default="ACTIVE", index=True)
    gate_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    shift_id: Mapped[int] = mapped_column(ForeignKey("shifts.id"), nullable=False, index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(nullable=True)
    plate_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(nullable=True)
    pricing_rule_id: Mapped[int | None] = mapped_column(ForeignKey("pricing_rules.id"), nullable=True)
    amount_charged: Mapped[int | None] = mapped_column(nullable=True)
    is_lost_card: Mapped[bool] = mapped_column(nullable=False, server_default="0")
    lost_card_penalty_applied: Mapped[int | None] = mapped_column(nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), nullable=False, server_default="cash")
    is_paid: Mapped[bool] = mapped_column(nullable=False, server_default="0")
    exit_operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    exit_shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id"), nullable=True)
    receipt_printed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    admin_override_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    admin_override_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(nullable=False, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True)
    is_subscribed: Mapped[bool] = mapped_column(nullable=False, server_default="0")
    plate_capture_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    plate_capture_requested_at: Mapped[datetime | None] = mapped_column(nullable=True)
    plate_captured_at: Mapped[datetime | None] = mapped_column(nullable=True)
    plate_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    plate_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plate_capture_error: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index(
            "idx_active_card_id",
            "card_id",
            unique=True,
            sqlite_where=text("exit_time IS NULL"),
            postgresql_where=text("exit_time IS NULL"),
        ),
    )

__all__ = ["SessionStatus", "PaymentMethod", "PlateCaptureStatus", "ParkingSession"]
