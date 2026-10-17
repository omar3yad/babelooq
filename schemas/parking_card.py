from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from models.parking_card import CardStatus

class ParkingCardCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    card_code: str = Field(min_length=1, max_length=50)

class ParkingCardBulkCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    card_codes: list[str] = Field(min_length=1, max_length=500)

class ParkingCardRangeCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    start_number: int = Field(ge=1)
    end_number: int = Field(ge=1)
    prefix: str = Field(default="", max_length=20)
    suffix: str = Field(default="", max_length=20)
    pad_zeros: int = Field(default=0, ge=0, le=10)

class ParkingCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    card_code: str
    status: CardStatus
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime

class ParkingCardStatusUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: CardStatus

__all__ = [
    "ParkingCardCreate",
    "ParkingCardBulkCreate",
    "ParkingCardRangeCreate",
    "ParkingCardResponse",
    "ParkingCardStatusUpdate",
]

