from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


def _split_env_list(value: str | None) -> List[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


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
    echidna_config_path: str | None = Field(
        default=os.environ.get("ECHIDNA_CONFIG_PATH")
    )
    echidna_seed_corpus: str | None = Field(
        default=os.environ.get("ECHIDNA_SEED_CORPUS")
    )
    echidna_test_limit: int | None = Field(default=None)
    echidna_property_filters: List[str] = Field(
        default_factory=lambda: _split_env_list(os.environ.get("ECHIDNA_PROPERTIES"))
    )
    echidna_extra_args: List[str] = Field(
        default_factory=lambda: _split_env_list(os.environ.get("ECHIDNA_EXTRA_ARGS"))
    )
    fuzz_budget_seconds: int | None = Field(default=None)
    default_timeout_seconds: int = 600
    tool_max_retries: int = 1

    @property
    def tool_attempts(self) -> int:
        """Total attempts per tool including the initial run."""

        return max(1, self.tool_max_retries + 1)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
