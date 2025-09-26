from typing import List
from loguru import logger
from app.schemas.browser_events import BrowserEvent, EventSegment


class EventSegmentationService:
    """Service for segmenting browser events into candidate workflows"""

    def __init__(self):
        # Configuration parameters
        self.min_segment_duration_ms = 5000  # 5 seconds minimum
        self.max_segment_duration_ms = 300000  # 5 minutes maximum
        self.max_gap_between_events_ms = 30000  # 30 seconds max gap
        self.min_events_per_segment = 3
        self.max_events_per_segment = 50

        # Event type weights for importance
        self.event_weights = {
            "page-load": 3.0,
            "click": 2.0,
            "type": 2.5,
            "highlight": 1.5,
            "copy": 2.0,
            "paste": 2.0,
            "tab-switch": 1.0,
            "tab-removal": 0.5,
        }

    async def segment_events(self, events: List[BrowserEvent]) -> List[EventSegment]:
        """
        Main segmentation algorithm that identifies workflow candidates

        Args:
            events: List of browser interaction events

        Returns:
            List of event segments representing potential workflows
        """
        if not events:
            return []

        logger.info(f"Starting event segmentation for {len(events)} events")

        # Step 1: Sort events by timestamp
        events = sorted(events, key=lambda x: x.timestamp)

        # Step 2: Identify natural break points
        break_points = await self._identify_break_points(events)
        logger.info(f"Identified {len(break_points)} break points")

        # Step 3: Create segments based on break points
        segments = await self._create_segments(events, break_points)
        logger.info(f"Created {len(segments)} initial segments")

        # Step 4: Filter and classify segments
        filtered_segments = await self._filter_and_classify_segments(segments)
        logger.info(f"Filtered to {len(filtered_segments)} valid segments")

        # Step 5: Calculate confidence scores
        scored_segments = await self._calculate_confidence_scores(filtered_segments)
        logger.info(f"Calculated confidence scores for {len(scored_segments)} segments")

        return scored_segments

    async def _identify_break_points(self, events: List[BrowserEvent]) -> List[int]:
        """
        Identify natural break points in the event sequence

        Break points occur at:
        - Large time gaps between events
        - Tab switches
        - Page loads (new context)
        - Domain changes
        """
        if len(events) < 2:
            return []

        break_points = [0]  # Start with first event

        for i in range(1, len(events)):
            current = events[i]
            previous = events[i - 1]

            # Check for large time gap
            time_gap = current.timestamp - previous.timestamp
            if time_gap > self.max_gap_between_events_ms:
                break_points.append(i)
                continue

            # Check for tab switch
            if current.type == "tab-switch":
                break_points.append(i)
                continue

            # Check for page load (new context)
            if current.is_page_load:
                break_points.append(i)
                continue

            # Check for domain change
            current_domain = current.domain
            previous_domain = previous.domain
            if current_domain and previous_domain and current_domain != previous_domain:
                break_points.append(i)
                continue

        # Add end point
        break_points.append(len(events))

        return break_points

    async def _create_segments(self, events: List[BrowserEvent], break_points: List[int]) -> List[EventSegment]:
        """Create segments based on break points"""
        segments = []

        for i in range(len(break_points) - 1):
            start_idx = break_points[i]
            end_idx = break_points[i + 1]

            if end_idx - start_idx < self.min_events_per_segment:
                continue

            segment_events = events[start_idx:end_idx]

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
                confidence_score=0.0,
                segment_type="unknown",
            )

            segments.append(segment)

        return segments

    async def _filter_and_classify_segments(self, segments: List[EventSegment]) -> List[EventSegment]:
        """Filter segments and classify their types"""
        filtered = []

        for segment in segments:
            # Filter by event count
            if len(segment.events) < self.min_events_per_segment:
                continue

            if len(segment.events) > self.max_events_per_segment:
                continue

            # Classify segment type
            segment.segment_type = await self._classify_segment_type(segment)

            # Skip segments that don't seem meaningful
            if segment.segment_type == "noise":
                continue

            filtered.append(segment)

        return filtered

    async def _classify_segment_type(self, segment: EventSegment) -> str:
        """Classify the type of segment based on event patterns"""
        event_types = segment.event_types
        unique_types = set(event_types)

        # Page session: mostly page-load events
        if event_types.count("page-load") > len(event_types) * 0.5:
            return "page_session"

        # Form filling: lots of typing events
        if event_types.count("type") > 3:
            return "form_filling"

        # Navigation: clicks and page loads
        if "click" in unique_types and "page-load" in unique_types:
            return "navigation"

        # Content interaction: highlighting, copying, pasting
        if any(t in unique_types for t in ["highlight", "copy", "paste"]):
            return "content_interaction"

        # Search: typing in search-like contexts
        if event_types.count("type") > 1 and any(
            "search" in event.url.lower() for event in segment.events if event.url
        ):
            return "search"

        # Single action: mostly one type of event
        if len(unique_types) == 1:
            return "single_action"

        # Mixed activity
        if len(unique_types) > 3:
            return "mixed_activity"

        return "unknown"

    async def _calculate_confidence_scores(self, segments: List[EventSegment]) -> List[EventSegment]:
        """Calculate confidence scores for segments"""
        for segment in segments:
            score = 0.0

            # Base score from event types
            for event_type in segment.event_types:
                score += self.event_weights.get(event_type, 1.0)

            # Normalize by duration (longer segments get higher scores)
            duration_minutes = segment.duration_ms / 60000
            score *= 1 + duration_minutes * 0.1

            # Bonus for meaningful segment types
            type_bonuses = {
                "form_filling": 1.5,
                "navigation": 1.2,
                "content_interaction": 1.3,
                "search": 1.4,
                "mixed_activity": 1.1,
            }

            score *= type_bonuses.get(segment.segment_type, 1.0)

            # Normalize to 0-1 range
            segment.confidence_score = min(score / 20.0, 1.0)

        return segments
