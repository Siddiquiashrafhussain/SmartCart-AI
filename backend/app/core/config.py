"""
SmartCart AI - Application Configuration
Managed via Pydantic BaseSettings with .env support.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Gateway Settings
    APP_NAME: str = "SmartCart AI API"
    APP_ENV: str = Field(default="development", description="Environment: development, test, production")
    APP_PORT: int = Field(default=8000, description="Listening port for FastAPI server")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = Field(default="smartcart-dev-insecure-secret-key-change-in-prod", description="Secret key for JWT/tokens")

    # Database Configuration (PostgreSQL primary, SQLite fallback for local test/dev)
    DATABASE_URL: str = Field(
        default="sqlite:///./smartcart.db",
        description="Database connection URL (PostgreSQL in production, SQLite for local dev/testing)"
    )
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Max overflow connections")

    # CORS Allowed Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Verification & Telemetry Parameters
    CORRELATION_WINDOW_SECONDS: float = Field(default=15.0, description="Max time delta tau for event correlation")
    WEIGHT_TOLERANCE_GRAMS: float = Field(default=50.0, description="Tolerance in grams for weight discrepancy detection")
    MIN_VERIFICATION_CONFIDENCE: float = Field(default=0.85, description="Threshold for automatic transaction verification")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Union[str, None]) -> str:
        if not v:
            return "sqlite:///./smartcart.db"
        # Support postgres:// -> postgresql:// for SQLAlchemy compatibility
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg://", 1)
        if v.startswith("postgresql://") and "+psycopg" not in v:
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
