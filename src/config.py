"""
Configuration module for API Key Management Service.
Loads and validates environment variables from .env files.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    environment: str = "development"
    api_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000

    # Vercel deployment (auto-detected)
    vercel: Optional[str] = None

    # Database configuration
    database_url: Optional[str] = None
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Security
    secret_key: str = "insecure-default-key-change-this"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # BetterStack (Logtail) Configuration
    betterstack_source_token: Optional[str] = None
    betterstack_ingesting_host: str = "in.logtail.com"

    # Monitoring & Health
    health_check_enabled: bool = True
    db_health_check_timeout: int = 5

    # Sanitization (global defaults; can be overridden per field via DB/control table)
    sanitization_strategy: str = "redact"  # redact | mask
    sanitization_replacement: str = "[REDACTED]"
    sanitization_mask_show_start: int = 3
    sanitization_mask_show_end: int = 2
    sanitization_mask_char: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def is_vercel(self) -> bool:
        """Check if running on Vercel platform."""
        return self.vercel is not None

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def betterstack_enabled(self) -> bool:
        """Check if BetterStack logging is enabled."""
        return (
            self.betterstack_source_token is not None
            and len(self.betterstack_source_token) > 0
            and self.is_production
        )

    def get_environment_class(self) -> str:
        """Get CSS class name for environment badge."""
        env_classes = {
            "production": "env-production",
            "staging": "env-staging",
            "development": "env-development",
        }
        return env_classes.get(self.environment.lower(), "env-development")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

