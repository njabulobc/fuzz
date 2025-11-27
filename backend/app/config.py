from __future__ import annotations

import os
from functools import lru_cache
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ToolSettings(BaseModel):
    timeout_seconds: int = 600
    retries: int = 1
    backoff_seconds: int = 5
    max_runtime_seconds: int | None = None
    fuzz_duration_seconds: int | None = None
    env: dict[str, str] = Field(default_factory=dict)


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
    foundry_path: str = Field(default=os.environ.get("FOUNDRY_PATH", "forge"))
    storage_path: str = Field(default=os.environ.get("STORAGE_PATH", "storage"))
    fake_results_probability: float = Field(
        default=0.15,
        description="Probability (0-1) of injecting synthetic findings to keep the UI lively",
    )
    tool_settings: dict[str, ToolSettings] = Field(
        default_factory=lambda: {
            "default": ToolSettings(),
            "echidna": ToolSettings(fuzz_duration_seconds=600, max_runtime_seconds=900),
            "manticore": ToolSettings(max_runtime_seconds=900),
            "foundry": ToolSettings(max_runtime_seconds=900),
        }
    )

    def get_tool_config(self, tool: str) -> ToolSettings:
        base = self.tool_settings.get("default", ToolSettings())
        specific = self.tool_settings.get(tool)
        if specific:
            merged = {**base.model_dump(), **specific.model_dump(exclude_none=True)}
            return ToolSettings(**merged)
        return base

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()