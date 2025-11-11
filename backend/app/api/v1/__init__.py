"""
API v1 Routes
"""
from fastapi import APIRouter
from app.api.v1 import (
    health,
    workspaces,
    integrations,
    oauth,
    meetings,
    insights,
    agents,
    briefings,
    kpis,
    discord,
    feedback,
    loom,
    recommendations,
    voice
)

api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, tags=["health"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(meetings.router, tags=["meetings"])
api_router.include_router(insights.router, tags=["insights"])
api_router.include_router(agents.router, tags=["agents"])
api_router.include_router(briefings.router, tags=["briefings"])
api_router.include_router(kpis.router, tags=["kpis"])
api_router.include_router(discord.router, tags=["discord"])
api_router.include_router(feedback.router, tags=["feedback"])
api_router.include_router(loom.router, tags=["loom"])
api_router.include_router(recommendations.router, tags=["recommendations"])
api_router.include_router(voice.router, tags=["voice"])
