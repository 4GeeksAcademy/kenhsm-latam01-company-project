"""Application settings loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Set a unique random value of at least 32 characters in every environment.
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    password_reset_token_expire_minutes: int = Field(default=30, ge=15, le=60)
    agent_query_limit_per_minute: int = Field(default=20, ge=1, le=1000)

    tinydb_path: str = "data/db.json"
    supabase_url: str | None = None
    supabase_secret_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    rfp_checkpoint_path: str = "data/state/rfp_approval_checkpoints.sqlite3"
    telemetry_endpoint: str = "http://localhost:8000/telemetry/events"

    resend_api_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"
    frontend_base_url: str = "http://localhost:3000"

    # Comma-separated allow-list of origins permitted to call this API from a browser.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5500,http://127.0.0.1:5500"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
