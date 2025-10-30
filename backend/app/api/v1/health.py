"""
Health Check Endpoints
System health and version information
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime

from app.config import get_settings, Settings
from app.database import db_manager

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    database: dict


class VersionResponse(BaseModel):
    """Version information response"""
    version: str
    api_version: str
    environment: str


@router.get("/health", response_model=HealthResponse, summary="Health Check")
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Comprehensive health check endpoint

    Returns system health status including:
    - API status
    - Database connectivity
    - Version information
    - Environment details

    This endpoint is used by monitoring systems and load balancers
    to verify service availability.
    """
    # Check database health
    db_health = await db_manager.health_check()

    return HealthResponse(
        status="healthy" if db_health["status"] == "healthy" else "degraded",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        environment=settings.environment,
        database=db_health
    )


@router.get("/version", response_model=VersionResponse, summary="API Version")
async def get_version(settings: Settings = Depends(get_settings)):
    """
    Get API version information

    Returns:
    - Application version
    - API version prefix
    - Environment name

    Useful for client compatibility checks and debugging.
    """
    return VersionResponse(
        version=settings.app_version,
        api_version=settings.api_v1_prefix,
        environment=settings.environment
    )


@router.get("/ping", summary="Simple Ping")
async def ping():
    """
    Simple ping endpoint for basic connectivity checks

    Returns a minimal response with timestamp.
    Useful for quick health checks without database queries.
    """
    return {
        "message": "pong",
        "timestamp": datetime.utcnow().isoformat()
    }
