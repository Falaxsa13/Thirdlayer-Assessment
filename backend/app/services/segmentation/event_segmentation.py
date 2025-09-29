from typing import List, Optional
from loguru import logger
from app.schemas.browser_events import BrowserEvent
from app.schemas.page_sessions import PageSession, PageSegment
from app.services.segmentation.page_service import PageService
from app.services.segmentation.intent_classification_service import IntentClassificationService


class EventSegmentationService:
    """Service for segmenting browser events into candidate workflows"""

    def __init__(self):
        self.page_service = PageService()
        self.intent_classifier = IntentClassificationService()

        self.min_segment_duration_ms = 2000  # 2 seconds minimum
        self.max_segment_duration_ms = 600000  # 10 minutes maximum

    async def generate_candidate_workflows(self, events: List[BrowserEvent]) -> List[PageSegment]:
        """Hierarchical segmentation: events -> page sessions -> candidate workflows (multi-page)"""
        if not events:
            return []

        # Step 1: Convert events to page-level summaries
        page_sessions: List[PageSession] = await self.page_service.group_events_into_page_sessions(events)
        # Step 2: Segment page sessions into candidate workflows (multi-page segments)
        candidate_workflows: List[PageSegment] = await self._process_page_sessions(page_sessions)

        return candidate_workflows

    async def _process_page_sessions(self, page_sessions: List[PageSession]) -> List[PageSegment]:
        """Segment page sessions into candidate workflows (multi-page segments)"""
        if not page_sessions:
            return []

        # Use page-level breakpoints
        page_segments: List[List[PageSession]] = await self._find_page_breakpoints(page_sessions)

        # Process page segments and classify them
        candidate_workflows = []
        for page_segment in page_segments:
            workflow_segment = await self._process_page_segment(page_segment)
            if workflow_segment:
                candidate_workflows.append(workflow_segment)

        return candidate_workflows

    async def _find_page_breakpoints(self, page_sessions: List[PageSession]) -> List[List[PageSession]]:
        """Detect breakpoints between page sessions"""
        segments = []
        current_segment = []

        for i, page in enumerate(page_sessions):
            if not current_segment:
                current_segment.append(page)
                continue

            previous_page = current_segment[-1]

            # Page-level breakpoint detection
            if self._is_page_breakpoint(page, previous_page):
                if len(current_segment) >= 1:  # At least 1 page per segment
                    segments.append(current_segment)
                current_segment = [page]
            else:
                current_segment.append(page)

        # Add the last segment
        if current_segment:
            segments.append(current_segment)

        return segments

    def _is_page_breakpoint(self, current: PageSession, previous: PageSession) -> bool:
        """Detect breakpoints between page sessions"""
        # Domain change
        if current.domain != previous.domain:
            return True

        # Large time gap
        if current.start_time - previous.end_time > 120000:  # 2 minutes
            return True

        # Tab change
        if current.tab_id != previous.tab_id:
            return True

        return False

    async def _process_page_segment(self, page_segment: List[PageSession]) -> Optional[PageSegment]:
        """Process page segment and classify it as a multi-page workflow"""
        if not page_segment:
            return None

        # Calculate segment properties
        start_time = page_segment[0].start_time
        end_time = page_segment[-1].end_time
        duration_ms = end_time - start_time

        # Skip segments that are too short or too long
        if duration_ms < self.min_segment_duration_ms or duration_ms > self.max_segment_duration_ms:
            return None

        # Classify the segment using intent classifier
        segment_type, tool_categories = await self.intent_classifier.classify_segment_intent(page_segment)

        # Skip segments that don't seem meaningful
        if segment_type == "unknown":
            return None

        # Create PageSegment with classified intent
        return PageSegment(pages=page_segment, segment_type=segment_type, tool_categories=tool_categories)
