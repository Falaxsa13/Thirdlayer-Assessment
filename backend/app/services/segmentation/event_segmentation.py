from typing import List
from loguru import logger
from app.schemas.browser_events import BrowserEvent, EventSegment
from app.services.segmentation.breakpoint_detector import BreakpointDetector
from app.services.segmentation.intent_classification_service import IntentClassificationService


class EventSegmentationService:
    """Service for segmenting browser events into candidate workflows"""

    def __init__(self):
        # Initialize services
        self.breakpoint_detector = BreakpointDetector()
        self.intent_classifier = IntentClassificationService()

        # Configuration parameters
        self.min_segment_duration_ms = 2000  # 2 seconds minimum (reduced for testing)
        self.max_segment_duration_ms = 600000  # 10 minutes maximum
        self.min_events_per_segment = 3
        self.max_events_per_segment = 100

    async def segment_events(self, events: List[BrowserEvent]) -> List[EventSegment]:
        """Main segmentation algorithm that identifies workflow candidates"""
        if not events:
            return []

        logger.info(f"Starting event segmentation for {len(events)} events")

        # Step 1: Use breakpoint detector to get initial segments
        event_segments = await self.breakpoint_detector.detect_breakpoints(events)
        logger.info(f"Breakpoint detector created {len(event_segments)} initial segments")

        # Step 2: Convert event segments to EventSegment objects
        segments: List[EventSegment] = await self._convert_to_event_segments(event_segments)
        logger.info(f"Converted to {len(segments)} EventSegment objects")

        # Step 3: Filter and classify segments using intent classifier
        filtered_segments = await self._filter_and_classify_segments(segments)
        logger.info(f"Filtered to {len(filtered_segments)} valid segments")

        return filtered_segments

    async def _convert_to_event_segments(self, event_segments: List[List[BrowserEvent]]) -> List[EventSegment]:
        """Convert list of event lists to EventSegment objects"""
        segments = []

        for segment_events in event_segments:
            if len(segment_events) < self.min_events_per_segment:
                continue

            # Calculate segment properties
            start_time = segment_events[0].timestamp
            end_time = segment_events[-1].timestamp
            duration = end_time - start_time

            # Skip segments that are too short or too long
            if duration < self.min_segment_duration_ms or duration > self.max_segment_duration_ms:
                continue

            # Get event types
            event_types = [event.type for event in segment_events]

            # Extract domain and tab info
            domain = segment_events[0].domain
            tab_id = segment_events[0].tab_id

            segment = EventSegment(
                events=segment_events,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration,
                event_types=event_types,
                domain=domain,
                tab_id=tab_id,
                segment_type="unknown",
            )

            segments.append(segment)

        return segments

    async def _filter_and_classify_segments(self, segments: List[EventSegment]) -> List[EventSegment]:
        """Filter segments and classify their types using intent classifier"""
        filtered = []

        for segment in segments:
            # Filter by event count
            if len(segment.events) < self.min_events_per_segment:
                continue

            if len(segment.events) > self.max_events_per_segment:
                continue

            # Classify segment type using intent classifier
            segment.segment_type = await self.intent_classifier.classify_segment_intent(segment)

            # Skip segments that don't seem meaningful
            if segment.segment_type == "unknown":
                continue

            filtered.append(segment)

        return filtered
