from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict
from models.user import UserRole

class UserBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=60, pattern=r"^[a-zA-Z0-9_]+$")
    role: UserRole
    gate_number: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def validate_role_gate(self) -> "UserBase":
        if self.role == UserRole.OPERATOR and self.gate_number is None:
            raise ValueError("Gate number is required for operators")
        if self.role == UserRole.ADMIN and self.gate_number is not None:
            raise ValueError("Gate number must be null for admin")
        return self

class UserCreate(UserBase):
    password: str = Field(min_length=4, max_length=128)

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserUpdatePassword(BaseModel):
    new_password: str = Field(min_length=4, max_length=128)

class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    gate_number: int | None = Field(default=None, ge=1, le=5)
    role: UserRole | None = None

