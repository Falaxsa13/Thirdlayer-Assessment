from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.schemas.browser_events import BrowserEvent


class EventBatchRequest(BaseModel):
    """Request structure for receiving events from Chrome extension"""

    events: List[BrowserEvent] = Field(..., description="List of browser events")
    timestamp: int = Field(..., description="Timestamp when the batch was sent")


class EventBatchResponse(BaseModel):
    """Response structure for event processing"""

    success: bool = Field(..., description="True if the batch was processed successfully")
    message: str = Field(..., description="A descriptive message about the processing result")


class EventResponse(BrowserEvent):
    """Response schema for a single interaction event, including database timestamps"""

    created_at: datetime = Field(..., description="Timestamp when the event was created in the database")
    updated_at: datetime = Field(..., description="Timestamp when the event was last updated in the database")


class HealthResponse(BaseModel):
    """Basic health check response"""

    status: str = Field(..., description="Status of the API")
    app_name: str = Field(..., description="Name of the application")
    version: str = Field(..., description="Version of the application")
    timestamp: datetime = Field(..., description="Current UTC timestamp")
