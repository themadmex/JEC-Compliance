from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:
    BaseSettings = BaseModel  # type: ignore[assignment]
    SettingsConfigDict = None  # type: ignore[assignment]


class Settings(BaseSettings):
    """Environment-backed application settings."""

    app_name: str = "JEC Compliance Engine"
    environment: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="sqlite:///data/jec_soc2.db",
        alias="DATABASE_URL",
    )
    test_mode: bool = Field(default=False, alias="TEST_MODE")
    azure_client_id: str | None = Field(default=None, alias="AZURE_CLIENT_ID")
    azure_client_secret: str | None = Field(default=None, alias="AZURE_CLIENT_SECRET")
    azure_tenant_id: str | None = Field(default=None, alias="AZURE_TENANT_ID")
    sharepoint_site_url: str | None = Field(default=None, alias="SHAREPOINT_SITE_URL")
    sharepoint_drive_id: str | None = Field(default=None, alias="SHAREPOINT_DRIVE_ID")

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            populate_by_name=True,
        )

    def __init__(self, **data: object) -> None:
        if SettingsConfigDict is None:
            data = {**_load_dotenv(), **os.environ, **data}
        super().__init__(**data)


def _load_dotenv() -> dict[str, str]:
    env_path = Path(".env")
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@lru_cache
def get_settings() -> Settings:
    return Settings()
