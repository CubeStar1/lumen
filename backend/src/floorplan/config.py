from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr
    openai_model: str = "gpt-5.6-luna"
    openai_reasoning_effort: str | None = None
    max_image_side: int = 2048
    max_upload_bytes: int = 15 * 1024 * 1024
    data_dir: Path = Path("data")
    stored_image_side: int = 1600
    thumbnail_side: int = 320


@lru_cache
def get_settings() -> Settings:
    return Settings()
