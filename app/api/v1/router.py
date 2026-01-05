"""
API v1 router.
Includes all endpoint routers for version 1 of the API.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth

# Create main API router
api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth.router)

# Future routers will be added here:
# api_router.include_router(users.router)
# api_router.include_router(content.router)
# api_router.include_router(study.router)
# api_router.include_router(flashcards.router)
# api_router.include_router(ai.router)
# api_router.include_router(admin.router)