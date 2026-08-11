from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COMFY_HELPER_", env_file=".env", extra="ignore"
    )

    app_name: str = "comfy-helper"
    host: str = "127.0.0.1"
    port: int = 8000
    comfyui_url: AnyHttpUrl = "http://10.0.0.180:8188/"
    comfyui_timeout_seconds: float = 10.0
    artifact_dir: Path = Path("artifacts")


@lru_cache
def get_settings() -> Settings:
    return Settings()
