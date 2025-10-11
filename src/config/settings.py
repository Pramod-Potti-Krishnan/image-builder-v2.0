"""
Application Settings
===================

Centralized configuration management using Pydantic Settings.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Google Cloud / Vertex AI
    google_cloud_project: str
    vertex_ai_location: str = "us-central1"
    google_application_credentials: Optional[str] = None

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: Optional[str] = None
    supabase_bucket: str = "generated-images"

    # Database (Supabase PostgreSQL)
    database_url: Optional[str] = None

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_keys: Optional[str] = None  # Changed to string, will parse in __init__

    # Application Settings
    environment: str = "development"
    log_level: str = "INFO"
    max_image_size_mb: int = 10
    rate_limit_per_minute: int = 60

    # Feature Flags
    enable_background_removal: bool = True
    enable_transparent_png: bool = True
    enable_custom_aspect_ratios: bool = True

    # Railway / Production
    port: Optional[int] = None  # Railway sets PORT env var

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Parse API keys if provided as comma-separated string
        if self.api_keys and isinstance(self.api_keys, str):
            self._api_keys_list = [k.strip() for k in self.api_keys.split(',') if k.strip()]
        else:
            self._api_keys_list = []

        # Use Railway's PORT if available
        if self.port:
            self.api_port = self.port

    @property
    def api_keys_list(self) -> List[str]:
        """Get parsed API keys as list."""
        return self._api_keys_list

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Use this function to access settings throughout the application.
    Settings are cached for performance.
    """
    return Settings()
