"""Application settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_csv_setting(value: str) -> tuple[str, ...]:
    """Parse a comma-separated env setting into non-empty unique values."""

    values: list[str] = []
    for raw_value in value.split(","):
        parsed_value = raw_value.strip()
        if parsed_value and parsed_value not in values:
            values.append(parsed_value)

    return tuple(values)


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
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    host: str = Field(default="0.0.0.0", alias="VOCKY_HOST")
    port: int = Field(default=8000, alias="VOCKY_PORT")
    log_level: str = Field(default="INFO", alias="VOCKY_LOG_LEVEL")
    mcp_allowed_hosts: str = Field(default="", alias="VOCKY_MCP_ALLOWED_HOSTS")
    mcp_allowed_origins: str = Field(default="", alias="VOCKY_MCP_ALLOWED_ORIGINS")
    mcp_auth_token: str = Field(default="", alias="VOCKY_MCP_AUTH_TOKEN")
    admin_auth_token: str = Field(default="", alias="VOCKY_ADMIN_AUTH_TOKEN")
    api_auth_token: str = Field(default="", alias="VOCKY_API_AUTH_TOKEN")
    attachments_dir: str = Field(default="./attachments", alias="VOCKY_ATTACHMENTS_DIR")
    attachments_max_bytes: int = Field(
        default=5 * 1024 * 1024, alias="VOCKY_ATTACHMENTS_MAX_BYTES"
    )
    attachments_max_count: int = Field(default=10, alias="VOCKY_ATTACHMENTS_MAX_COUNT")
    attachments_allowed_mime_types: str = Field(
        default="image/jpeg,image/png,image/gif,image/webp",
        alias="VOCKY_ATTACHMENTS_ALLOWED_MIME_TYPES",
    )

    @property
    def mcp_allowed_host_values(self) -> tuple[str, ...]:
        """Return configured MCP Host allowlist additions."""

        return parse_csv_setting(self.mcp_allowed_hosts)

    @property
    def mcp_allowed_origin_values(self) -> tuple[str, ...]:
        """Return configured MCP Origin allowlist additions."""

        return parse_csv_setting(self.mcp_allowed_origins)

    @property
    def mcp_auth_token_value(self) -> str:
        """Return the configured MCP bearer token, or an empty string when disabled."""

        return self.mcp_auth_token.strip()

    @property
    def admin_auth_token_value(self) -> str:
        """Return the configured Admin REST bearer token, or an empty string when disabled."""

        return self.admin_auth_token.strip()

    @property
    def api_auth_token_value(self) -> str:
        """Return the configured public REST bearer token, or an empty string when disabled."""

        return self.api_auth_token.strip()

    @property
    def attachments_allowed_mime_type_values(self) -> tuple[str, ...]:
        """Return the configured allowed attachment MIME types."""

        return parse_csv_setting(self.attachments_allowed_mime_types)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
