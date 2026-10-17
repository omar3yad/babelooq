import os
from typing import Literal
import functools
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENVIRONMENT: Literal["development", "staging", "production"]
    DEBUG: bool = False
    APP_NAME: str = "garage4u"
    JWT_EXPIRE_HOURS: int = 8
    JWT_ALGORITHM: str = "HS256"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    CORS_ORIGINS: list[str] = []
    SEED_ADMIN_USERNAME: str | None = None
    SEED_ADMIN_PASSWORD: str | None = None
    SEED_ADMIN_FULL_NAME: str | None = None

    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if self.ENVIRONMENT == "production" and self.DEBUG is True:
            raise ValueError("DEBUG must not be True in production")
        if self.JWT_EXPIRE_HOURS < 1:
            raise ValueError("JWT_EXPIRE_HOURS must be at least 1")
        return self

@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()

__all__ = ["Settings", "get_settings"]
