from pydantic import BaseModel, Field
from typing import List, Optional


class PageSession(BaseModel):
    """Represents a summarized page session"""

    url: str = Field(..., description="Page URL")
    title: str = Field(..., description="Page title")
    start_time: int = Field(..., description="Start timestamp in milliseconds")
    end_time: int = Field(..., description="End timestamp in milliseconds")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    content_summary: str = Field(..., description="Summarized page content")
    event_count: int = Field(..., description="Number of events on this page")
    domain: Optional[str] = Field(None, description="Domain of the page")
    tab_id: Optional[int] = Field(None, description="Browser tab ID")
    segment_type: str = Field("unknown", description="Type of segment (form_filling, navigation, etc.)")
    tool_categories: List[str] = Field(default_factory=list, description="Tool categories needed for this segment")


class PageSegment(BaseModel):
    """Represents a group of related page sessions that form a workflow"""

    pages: List[PageSession] = Field(..., description="List of page sessions in this segment")
    segment_type: str = Field("unknown", description="Type of segment (form_filling, navigation, etc.)")
    tool_categories: List[str] = Field(default_factory=list, description="Tool categories needed for this segment")

    @property
    def start_time(self) -> int:
        """Get start time of the first page"""
        return self.pages[0].start_time if self.pages else 0

    @property
    def end_time(self) -> int:
        """Get end time of the last page"""
        return self.pages[-1].end_time if self.pages else 0

    @property
    def duration_ms(self) -> int:
        """Get total duration of the segment"""
        return self.end_time - self.start_time

    @property
    def domain(self) -> Optional[str]:
        """Get domain of the first page"""
        return self.pages[0].domain if self.pages else None
