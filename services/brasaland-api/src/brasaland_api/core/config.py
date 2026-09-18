"""Application settings loaded from environment variables / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # JWT signing key. Must be overridden via .env in every environment.
    secret_key: str = "CHANGE-ME-INSECURE-DEV-ONLY-SECRET"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    tinydb_path: str = "data/db.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
