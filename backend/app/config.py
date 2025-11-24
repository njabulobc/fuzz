from __future__ import annotations

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "scan-platform"
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@db:5432/scan"
    )
    redis_url: str = Field(default="redis://redis:6379/0")
    celery_broker_url: str = Field(default="redis://redis:6379/1")
    celery_result_backend: str = Field(default="redis://redis:6379/2")
    slither_path: str = Field(default=os.environ.get("SLITHER_PATH", "slither"))
    mythril_path: str = Field(default=os.environ.get("MYTHRIL_PATH", "myth"))
    echidna_path: str = Field(default=os.environ.get("ECHIDNA_PATH", "echidna-test"))
    manticore_path: str = Field(default=os.environ.get("MANTICORE_PATH", "manticore"))
    default_timeout_seconds: int = 600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()