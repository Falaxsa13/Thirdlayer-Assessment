from typing import Optional, List, Union, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ElementInfo(BaseModel):
    """Information about a DOM element involved in an event"""

    tag: str = Field(..., description="HTML tag name")
    id: Optional[str] = Field(None, description="Element ID")
    class_name: Optional[str] = Field(None, description="Element class name")
    text: Optional[str] = Field(None, description="Element text content")
    aria_label: Optional[str] = Field(None, description="ARIA label")
    role: Optional[str] = Field(None, description="ARIA role")
    href: Optional[str] = Field(None, description="Link href (for anchor tags)")


class EventPayload(BaseModel):
    """Payload data specific to different event types"""

    element: Optional[ElementInfo] = Field(None, description="Element information for click/hover events")
    text: Optional[str] = Field(None, description="Text content for type/highlight events")
    previous_text: Optional[str] = Field(None, description="Previous text for type events")
    triggered_by: Optional[str] = Field(None, description="What triggered the event (e.g., 'enter', 'click')")
    duration: Optional[int] = Field(None, description="Event duration in milliseconds")
    markdown: Optional[str] = Field(None, description="Page content in markdown format")
    scroll_position: Optional[dict] = Field(None, description="Scroll position data")
    viewport_size: Optional[dict] = Field(None, description="Viewport dimensions")
    mouse_position: Optional[dict] = Field(None, description="Mouse position coordinates")


class BrowserEvent(BaseModel):
    """A single browser interaction event"""

    id: str = Field(..., description="Unique event identifier")
    type: str = Field(..., description="Event type (click, type, page-load, etc.)")
    timestamp: int = Field(..., description="Event timestamp in milliseconds since epoch")
    tab_id: Optional[int] = Field(None, description="Browser tab ID")
    window_id: Optional[int] = Field(None, description="Browser window ID")
    url: Optional[str] = Field(None, description="URL where event occurred")
    title: Optional[str] = Field(None, description="Page title where event occurred")
    payload: Optional[EventPayload] = Field(None, description="Event-specific data")

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


class EventSegment(BaseModel):
    """Represents a segment of events that form a potential workflow"""

    events: List[BrowserEvent] = Field(..., description="Events in this segment")
    start_time: int = Field(..., description="Start timestamp of the segment")
    end_time: int = Field(..., description="End timestamp of the segment")
    duration_ms: int = Field(..., description="Duration of the segment in milliseconds")
    event_types: List[str] = Field(..., description="Types of events in this segment")
    domain: Optional[str] = Field(None, description="Primary domain for this segment")
    tab_id: Optional[int] = Field(None, description="Primary tab ID for this segment")
    segment_type: str = Field("unknown", description="Type of segment (form_filling, navigation, etc.)")

    @property
    def unique_event_types(self) -> set[str]:
        """Get unique event types in this segment"""
        return set(self.event_types)

    @property
    def duration_minutes(self) -> float:
        """Get duration in minutes"""
        return self.duration_ms / 60000.0

    @property
    def event_count(self) -> int:
        """Get number of events in this segment"""
        return len(self.events)


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
