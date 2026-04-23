"""Application settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Vocky service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    app_name: str = "Vocky"
    database_url: str = Field(alias="DATABASE_URL")
    host: str = Field(default="0.0.0.0", alias="VOCKY_HOST")
    port: int = Field(default=8000, alias="VOCKY_PORT")
    log_level: str = Field(default="INFO", alias="VOCKY_LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
