"""Application configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "SeedArr"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./config/seedarr.db"

    # Security
    secret_key: str = "change-this-in-production-with-a-secure-key"

    # Server
    host: str = "0.0.0.0"
    port: int = 8585

    # Scheduler
    default_scan_interval_minutes: int = 15

    # Paths
    config_path: Path = Path("/config")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
