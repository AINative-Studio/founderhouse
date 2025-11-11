"""
Test fixtures for webhook tests
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.webhooks import zoom_webhook, fireflies_webhook, otter_webhook


@pytest.fixture
def webhook_app():
    """Create a FastAPI test app with webhook routers"""
    app = FastAPI()

    # Include webhook routers
    app.include_router(zoom_webhook.router, prefix="/api")
    app.include_router(fireflies_webhook.router, prefix="/api")
    app.include_router(otter_webhook.router, prefix="/api")

    return app


@pytest.fixture
def webhook_client(webhook_app):
    """Create test client for webhook app"""
    return TestClient(webhook_app)
