"""
API v1 Routes
"""
from fastapi import APIRouter
from app.api.v1 import health, workspaces, integrations, oauth

api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, tags=["health"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
