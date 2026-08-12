"""Application settings, overridable via environment variables."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRIVATEPERP_", env_file=".env")

    app_name: str = "PrivatePerp Risk Engine API"
    api_version: str = "0.1.0"
    # NoDecode suppresses the JSON decoding pydantic-settings applies to
    # collection fields, which would otherwise reject a plain string before the
    # validator below ever sees it.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    cors_origin_regex: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _accept_comma_separated(cls, value: object) -> object:
        """Accept ``a,b`` as well as a JSON array.

        Hosting dashboards take a plain text value, and requiring JSON there is a
        reliable way to spend an afternoon debugging CORS instead of deploying.
        The JSON form is still honoured because it is what the pydantic-settings
        documentation shows.
        """
        if not isinstance(value, str):
            return value
        if not value.strip():
            # An empty variable means "not configured", not "allow nothing".
            # Hosting dashboards make it easy to submit a blank value, and
            # silently blocking every origin is a miserable thing to debug.
            return cls.model_fields["cors_origins"].default
        if value.lstrip().startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
