"""
Application Configuration
Uses Pydantic BaseSettings for environment-based configuration
"""
from functools import lru_cache
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "AI Chief of Staff API"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Enable debug mode")

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )

    # ZeroDB Configuration
    # PostgreSQL with 60+ database service endpoints
    # Includes vector search, embeddings, events, full-text search, and more
    zerodb_email: str = Field(default="admin@ainative.studio", description="ZeroDB user email")
    zerodb_username: str = Field(default="admin@ainative.studio", description="ZeroDB username")
    zerodb_password: str = Field(default="demo-password", description="ZeroDB password")
    zerodb_api_base_url: str = Field(default="https://api.ainative.studio", description="ZeroDB API base URL")
    zerodb_api_key: str = Field(default="demo-key", description="ZeroDB API key")
    zerodb_project_id: str = Field(default="demo-project", description="ZeroDB project ID")

    # Database Connection (for direct PostgreSQL access)
    zerodb_host: str = Field(default="localhost", description="Database host")
    zerodb_port: int = Field(default=5432, description="Database port")
    zerodb_database: str = Field(default="founderhouse", description="Database name")
    zerodb_user: str = Field(default="postgres", description="Database user")

    # Database Configuration
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Max overflow connections")

    # Security
    secret_key: str = Field(default="demo-secret-key-for-local-development-minimum-32-chars-long", description="Secret key for JWT encoding")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, description="Max requests per minute per IP")

    # External Services (MCP Integrations)
    zoom_client_id: Optional[str] = None
    zoom_client_secret: Optional[str] = None
    slack_client_id: Optional[str] = None
    slack_client_secret: Optional[str] = None
    discord_client_id: Optional[str] = None
    discord_client_secret: Optional[str] = None
    discord_bot_token: Optional[str] = None
    monday_api_key: Optional[str] = None
    notion_api_key: Optional[str] = None
    google_client_id: Optional[str] = None  # For Gmail
    google_client_secret: Optional[str] = None
    microsoft_client_id: Optional[str] = None  # For Outlook
    microsoft_client_secret: Optional[str] = None
    loom_client_id: Optional[str] = None
    loom_client_secret: Optional[str] = None
    otter_api_key: Optional[str] = None  # For transcription fallback

    # ZeroVoice MCP (Sprint 5 - voice → intent → action pipeline)
    zerovoice_api_base_url: str = Field(
        default="https://api.zerovoice.ainative.studio",
        description="ZeroVoice MCP API base URL for voice command processing"
    )
    zerovoice_api_key: Optional[str] = Field(
        default=None,
        description="ZeroVoice API key for authentication"
    )

    # Background Tasks
    enable_health_checks: bool = Field(default=True, description="Enable scheduled health checks")
    health_check_interval_hours: int = Field(default=6, description="Health check interval in hours")

    # Discord Daily Briefing Configuration
    enable_discord_briefings: bool = Field(default=True, description="Enable automated Discord briefings")
    discord_briefing_hour: int = Field(default=8, description="Hour to send Discord briefings (local time)")
    default_timezone: str = Field(default="UTC", description="Default timezone for briefings")

    # Vector Search Configuration
    embedding_dimension: int = Field(default=1536, description="Dimension of embedding vectors")
    vector_similarity_threshold: float = Field(default=0.7, description="Minimum similarity score for vector search")

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v

    @validator("allowed_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables not defined in model


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Uses lru_cache to ensure settings are loaded once
    """
    return Settings()


# Convenience function for dependency injection
def get_settings_dependency():
    """FastAPI dependency for settings injection"""
    return get_settings()
