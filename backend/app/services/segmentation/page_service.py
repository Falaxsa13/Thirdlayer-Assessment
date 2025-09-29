from typing import List, Dict, Optional
from loguru import logger
from collections import defaultdict

from app.schemas.browser_events import BrowserEvent
from app.schemas.page_sessions import PageSession


class PageService:
    """Summarizes page-level activities into clean summaries"""

    def __init__(self):
        self.min_page_duration_ms = 1000  # Minimum 1 second to be meaningful
        self.max_content_length = 500  # Truncate long content

        # Denoising parameters
        self.rapid_click_threshold_ms = 200  # Events within 200ms are rapid
        self.accidental_event_threshold_ms = 100  # Events under 100ms are accidental

    async def group_events_into_page_sessions(self, events: List[BrowserEvent]) -> List[PageSession]:
        """Convert events into page-level summaries"""
        if not events:
            return []
        # Group events by page (URL + tab)
        page_groups: Dict[str, List[BrowserEvent]] = self._group_events_by_page(events)

        summaries: List[PageSession] = []
        for _, page_events in page_groups.items():
            processed_page_session: Optional[PageSession] = await self._create_page_summary(page_events)

            if processed_page_session:
                summaries.append(processed_page_session)

        return summaries

    def _group_events_by_page(self, events: List[BrowserEvent]) -> Dict[str, List[BrowserEvent]]:
        """Group events by page (URL + tab combination)"""

        page_groups: Dict[str, List[BrowserEvent]] = defaultdict(list)

        for event in events:
            # Create page key from URL and tab
            page_key = f"{event.url or 'unknown'}:{event.tab_id or 0}"
            page_groups[page_key].append(event)

        for page_key in page_groups:
            page_groups[page_key].sort(key=lambda x: x.timestamp)

        return dict(page_groups)

    def _denoise_page_events(self, events: List[BrowserEvent]) -> List[BrowserEvent]:
        """Remove noise from events within a page"""
        if len(events) < 2:
            return events

        denoised: List[BrowserEvent] = []

        i = 0
        while i < len(events):
            current_event = events[i]

            # Skip rapid clicks on same element
            if self._is_rapid_click(current_event, events, i):
                i += 1
                continue

            # Skip accidental events (very short duration)
            if self._is_accidental_event(current_event, events, i):
                i += 1
                continue

            # Skip focus/blur noise
            if self._is_focus_blur_noise(current_event, events, i):
                i += 1
                continue

            denoised.append(current_event)
            i += 1

        return denoised

    def _is_rapid_click(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if this is a rapid click on the same element"""
        if event.type != "click" or index == 0:
            return False

        previous_event = events[index - 1]
        if previous_event.type != "click":
            return False

        time_gap = event.timestamp - previous_event.timestamp
        if time_gap > self.rapid_click_threshold_ms:
            return False

        # Same element (same URL + tab)
        return event.url == previous_event.url and event.tab_id == previous_event.tab_id

    def _is_accidental_event(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if the gap between the current and previous event is less than the accidental event threshold"""
        if index == 0:
            return False

        previous_event = events[index - 1]
        time_gap = event.timestamp - previous_event.timestamp

        return time_gap < self.accidental_event_threshold_ms

    def _is_focus_blur_noise(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if the current event is a focus/blur event and the previous event is not the same type"""
        if event.type not in ["focus", "blur"]:
            return False

        # Look for rapid focus/blur pairs
        if index > 0:
            prev_event = events[index - 1]
            if prev_event.type in ["focus", "blur"] and event.type != prev_event.type:
                time_gap = event.timestamp - prev_event.timestamp
                if time_gap < 500:  # 500ms threshold for focus/blur noise
                    return True

        return False

    async def _create_page_summary(self, events: List[BrowserEvent]) -> Optional[PageSession]:
        """Create a summary of activities on a single page"""

        if not events:
            return None

        # Denoise events within the page
        denoised_events: List[BrowserEvent] = self._denoise_page_events(events)
        if not denoised_events:
            return None

        # stats for the page session
        first_event: BrowserEvent = denoised_events[0]
        last_event: BrowserEvent = denoised_events[-1]
        duration_ms = last_event.timestamp - first_event.timestamp

        # Skip very short page sessions
        if duration_ms < self.min_page_duration_ms:
            return None

        # Get page content summary from denoised events
        content_summary = self._summarize_page_content(denoised_events)

        return PageSession(
            url=first_event.url or "unknown",
            title=first_event.title or "Unknown Page",
            start_time=first_event.timestamp,
            end_time=last_event.timestamp,
            duration_ms=duration_ms,
            content_summary=content_summary,
            event_count=len(events),
            domain=first_event.domain,
            tab_id=first_event.tab_id,
            segment_type="unknown",  # Will be set during classification
            tool_categories=[],  # Will be set during classification
        )

    def _summarize_page_content(self, events: List[BrowserEvent]) -> str:
        """Summarize page content from events"""
        content_parts = []

        for event in events:
            if event.payload:
                # Extract markdown from payload if available
                markdown = event.payload.get("markdown", "")
                if markdown:
                    # Truncate very long content
                    if len(markdown) > self.max_content_length:
                        markdown = markdown[: self.max_content_length] + "..."
                    content_parts.append(markdown)

        if content_parts:
            return " | ".join(content_parts)

        return "No content available"
