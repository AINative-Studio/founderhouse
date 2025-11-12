"""
FastAPI Main Application
AI Chief of Staff Backend API
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.api.v1 import api_router
from app.database import db_manager
from app.middleware.metrics import PrometheusMiddleware
from app.core.monitoring import set_app_info

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting AI Chief of Staff API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Initialize Prometheus metrics
    set_app_info(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment
    )
    logger.info("Prometheus metrics initialized")

    # Initialize database connection
    try:
        health = await db_manager.health_check()
        if health["status"] == "healthy":
            logger.info("Database connection established")
        else:
            logger.warning(f"Database health check failed: {health}")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        if settings.environment == "production":
            raise

    # Initialize background tasks
    if settings.enable_health_checks:
        try:
            from app.tasks.integration_health import init_scheduler
            init_scheduler()
            logger.info("Background task scheduler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize background tasks: {str(e)}")

    yield

    # Shutdown
    logger.info("Shutting down AI Chief of Staff API")

    # Stop background tasks
    if settings.enable_health_checks:
        try:
            from app.tasks.integration_health import stop_health_checks
            stop_health_checks()
            logger.info("Background task scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping background tasks: {str(e)}")

    db_manager.close()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    AI Chief of Staff Backend API

    A multi-agent executive operations system that acts as a founder's intelligent operator,
    synthesizing meetings, communications, documents, and metrics across dozens of tools
    through MCP (Model Context Protocol) servers.

    ## Features

    - **Multi-tenant Workspace Management**: Secure workspace isolation with RLS
    - **MCP Integration Framework**: Connect to Zoom, Slack, Discord, Monday, Notion, and more
    - **Meeting Intelligence**: Automatic transcription and summarization
    - **Communication Aggregation**: Unified inbox across all channels
    - **Task Management**: Bi-directional sync with Monday and Notion
    - **Vector Search**: Semantic search across all content using pgvector

    ## Authentication

    All endpoints require Bearer token authentication except health check endpoints.

    ```
    Authorization: Bearer <your_jwt_token>
    ```

    ## Rate Limiting

    API requests are limited to prevent abuse. Current limit: 100 requests/minute per IP.

    ## Support

    For issues and questions: https://github.com/AINative-Studio/founderhouse
    """,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json",
    lifespan=lifespan,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Add GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)


# Exception handlers

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail} - "
        f"Path: {request.url.path} - Method: {request.method}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc.errors()} - Path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed",
            "errors": exc.errors(),
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        f"Unexpected error: {str(exc)} - Path: {request.url.path}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "path": request.url.path
        }
    )


# Middleware for request logging

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    logger.info(
        f"Response: {request.method} {request.url.path} - "
        f"Status: {response.status_code}"
    )

    return response


# Include API routers
app.include_router(api_router, prefix=settings.api_v1_prefix)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirects to docs"""
    return {
        "message": "AI Chief of Staff API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
