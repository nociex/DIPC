"""API v1 package initialization."""

from fastapi import APIRouter
from .tasks import router as tasks_router
from .upload import router as upload_router
from .health import router as health_router

# Create the main API router for v1
api_router = APIRouter()

# Include sub-routers
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(upload_router, prefix="/upload", tags=["upload"])
api_router.include_router(health_router, prefix="/health", tags=["health"])