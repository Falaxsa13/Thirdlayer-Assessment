from fastapi import APIRouter
from app.api.v1.endpoints import events, workflow_generation

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(events.router, tags=["events"])
api_router.include_router(workflow_generation.router, prefix="/workflow-generation", tags=["workflow-generation"])
