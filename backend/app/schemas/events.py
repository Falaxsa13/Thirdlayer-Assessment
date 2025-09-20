from pydantic import BaseModel
from typing import Optional, Any, List
from datetime import datetime


class InteractionEvent(BaseModel):
    """TODO: Define interaction event structure from Chrome extension"""

    id: str
    type: str
    timestamp: int
    tab_id: Optional[int] = None
    window_id: Optional[int] = None
    url: Optional[str] = None
    title: Optional[str] = None
    payload: Optional[dict] = None


class EventBatchRequest(BaseModel):
    """TODO: Define request structure for receiving events from Chrome extension"""

    events: List[InteractionEvent]
    timestamp: int


class EventBatchResponse(BaseModel):
    """TODO: Define response structure for event processing"""

    success: bool
    message: str
    processed_count: int


class HealthResponse(BaseModel):
    """Basic health check response"""

    status: str
    app_name: str
    version: str
    timestamp: datetime
