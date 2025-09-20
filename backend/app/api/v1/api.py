from fastapi import APIRouter
from app.api.v1.endpoints import events, health, workflows, workflow_generation

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(workflow_generation.router, prefix="/workflow-generation", tags=["workflow-generation"])
