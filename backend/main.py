from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.core.database import create_tables
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Workflow Event Processor API...")
    create_tables()
    logger.info("Database tables created successfully")
    yield
    # Shutdown
    logger.info("Shutting down Workflow Event Processor API...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A modular FastAPI backend for processing browser interaction events and generating workflows",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Workflow Event Processor API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/v1/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host=settings.api_host, port=settings.api_port, reload=True, log_level=settings.log_level.lower()
    )
