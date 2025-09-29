from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BrowserEvent(BaseModel):
    """A single browser interaction event"""

    id: str = Field(..., description="Unique event identifier")
    type: str = Field(..., description="Event type (click, type, page-load, etc.)")
    timestamp: int = Field(..., description="Event timestamp in milliseconds since epoch")
    tab_id: Optional[int] = Field(None, description="Browser tab ID")
    window_id: Optional[int] = Field(None, description="Browser window ID")
    url: Optional[str] = Field(None, description="URL where event occurred")
    title: Optional[str] = Field(None, description="Page title where event occurred")
    payload: Optional[Dict[str, Any]] = Field(None, description="Event-specific data")

    # Computed fields
    @property
    def domain(self) -> Optional[str]:
        """Extract domain from URL"""
        if not self.url:
            return None
        try:
            from urllib.parse import urlparse

            parsed = urlparse(self.url)
            return parsed.netloc.lower()
        except:
            return None

    @property
    def is_page_load(self) -> bool:
        """Check if this is a page load event"""
        return self.type == "page-load"

    @property
    def is_click(self) -> bool:
        """Check if this is a click event"""
        return self.type == "click"

    @property
    def is_type_event(self) -> bool:
        """Check if this is a typing event"""
        return self.type == "type"

    @property
    def is_highlight(self) -> bool:
        """Check if this is a highlight event"""
        return self.type == "highlight"


class EventBatch(BaseModel):
    """A batch of browser events sent from the Chrome extension"""

    events: List[BrowserEvent] = Field(..., description="List of browser events")
    timestamp: int = Field(..., description="Timestamp when batch was sent")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")

    @property
    def event_count(self) -> int:
        """Get number of events in this batch"""
        return len(self.events)

    @property
    def duration_ms(self) -> int:
        """Get total duration of events in this batch"""
        if not self.events:
            return 0
        timestamps = [event.timestamp for event in self.events]
        return max(timestamps) - min(timestamps)

    @property
    def domains(self) -> set[str]:
        """Get unique domains in this batch"""
        domains = [event.domain for event in self.events if event.domain]
        return set(domains)
