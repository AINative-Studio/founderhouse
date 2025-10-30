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

    # Supabase Configuration
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon/service key")
    supabase_service_key: Optional[str] = Field(None, description="Supabase service role key for admin operations")

    # Database Configuration
    postgres_url: Optional[str] = Field(None, description="Direct Postgres connection URL (optional)")
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Max overflow connections")

    # Security
    secret_key: str = Field(..., description="Secret key for JWT encoding")
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
    discord_bot_token: Optional[str] = None
    monday_api_key: Optional[str] = None
    notion_api_key: Optional[str] = None

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
