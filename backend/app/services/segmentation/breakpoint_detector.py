from typing import List, Tuple
from loguru import logger

from app.schemas.browser_events import BrowserEvent


class BreakpointDetector:
    """Service for detecting natural break points in event sequences"""

    def __init__(self):
        # Configuration parameters for break point detection
        self.large_time_gap_ms = 120000  # 2 minutes - large time gap
        self.domain_change_threshold_ms = 30000  # 30 seconds - domain change break
        self.task_completion_signals = [
            "form_submit",
            "purchase_complete",
            "checkout_success",
            "signup_complete",
            "login_success",
            "download_complete",
        ]
        self.context_switch_indicators = ["tab-switch", "window-focus", "app-switch"]

    async def detect_breakpoints(self, events: List[BrowserEvent]) -> List[List[BrowserEvent]]:
        """
        Main method that detects break points and returns segmented events

        Args:
            events: List of browser interaction events

        Returns:
            List of event segments (each segment is a list of events)
        """
        if not events:
            return []

        logger.info(f"Starting breakpoint detection for {len(events)} events")

        # Sort events by timestamp to ensure proper order
        sorted_events = sorted(events, key=lambda x: x.timestamp)

        # Detect break points
        break_points = await self._identify_break_points(sorted_events)
        logger.info(f"Identified {len(break_points)} break points")

        # Create segments from break points
        segments = await self._create_segments(sorted_events, break_points)
        logger.info(f"Created {len(segments)} event segments")

        return segments

    async def _identify_break_points(self, events: List[BrowserEvent]) -> List[int]:
        """
        Identify natural break points in the event sequence

        Break points occur at:
        - Domain changes (different websites)
        - Large time gaps (>2 minutes)
        - Task completion signals (form submission, purchase)
        - Context switches (work → personal browsing)
        """
        if len(events) < 2:
            return [0, len(events)]

        break_points = [0]  # Start with first event

        for i in range(1, len(events)):
            current = events[i]
            previous = events[i - 1]

            # Check for domain change
            if await self._is_domain_change(current, previous):
                logger.debug(f"Domain change break point at index {i}: {previous.domain} → {current.domain}")
                break_points.append(i)
                continue

            # Check for large time gap
            if await self._is_large_time_gap(current, previous):
                logger.debug(f"Large time gap break point at index {i}: {current.timestamp - previous.timestamp}ms")
                break_points.append(i)
                continue

            # Check for task completion signals
            if await self._is_task_completion(current):
                logger.debug(f"Task completion break point at index {i}: {current.type}")
                break_points.append(i)
                continue

            # Check for context switches
            if await self._is_context_switch(current, previous):
                logger.debug(f"Context switch break point at index {i}: {current.type}")
                break_points.append(i)
                continue

            # Check for page load after significant activity
            if await self._is_significant_page_load(current, events, i):
                logger.debug(f"Significant page load break point at index {i}: {current.url}")
                break_points.append(i)
                continue

        # Add end point
        break_points.append(len(events))

        return break_points

    async def _create_segments(self, events: List[BrowserEvent], break_points: List[int]) -> List[List[BrowserEvent]]:
        """Create event segments based on break points"""
        segments = []

        for i in range(len(break_points) - 1):
            start_idx = break_points[i]
            end_idx = break_points[i + 1]

            if end_idx - start_idx < 1:  # Skip empty segments
                continue

            segment_events = events[start_idx:end_idx]

            # Filter out very short segments (less than 2 events)
            if len(segment_events) < 2:
                continue

            segments.append(segment_events)

        return segments

    async def _is_domain_change(self, current: BrowserEvent, previous: BrowserEvent) -> bool:
        """Check if this represents a domain change"""
        current_domain = current.domain
        previous_domain = previous.domain

        # No domain information available
        if not current_domain or not previous_domain:
            return False

        # Different domains
        if current_domain != previous_domain:
            return True

        return False

    async def _is_large_time_gap(self, current: BrowserEvent, previous: BrowserEvent) -> bool:
        """Check if there's a large time gap between events"""
        time_gap = current.timestamp - previous.timestamp
        return time_gap > self.large_time_gap_ms

    async def _is_task_completion(self, event: BrowserEvent) -> bool:
        """Check if this event represents task completion"""
        # Check event type
        if event.type in self.task_completion_signals:
            return True

        completion_patterns = [
            "success",
            "complete",
            "thank",
            "confirmation",
            "receipt",
            "order-confirmed",
            "payment-success",
            "order-completed",
            "order-shipped",
            "order-delivered",
            "order-received",
            "order-paid",
            "order-confirmed",
            "order-completed",
        ]

        # Check URL patterns for completion signals
        if event.url:
            url_lower = event.url.lower()
            if any(pattern in url_lower for pattern in completion_patterns):
                return True

        # Check page title for completion signals
        if event.title:
            title_lower = event.title.lower()
            if any(pattern in title_lower for pattern in completion_patterns):
                return True

        return False

    async def _is_context_switch(self, current: BrowserEvent, previous: BrowserEvent) -> bool:
        """Check if this represents a context switch"""
        # Check for explicit context switch events
        if current.type in self.context_switch_indicators:
            return True

        # Check for significant tab changes
        if (
            current.type == "tab-switch"
            and current.tab_id != previous.tab_id
            and current.timestamp - previous.timestamp > 5000
        ):  # 5 seconds threshold
            return True

        return False

    async def _is_significant_page_load(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if this is a significant page load after substantial activity"""
        if not event.is_page_load:
            return False

        # Look back to see if there was substantial activity before this page load
        activity_threshold = 5  # events
        time_threshold = 30000  # 30 seconds

        activity_count = 0
        start_time = event.timestamp - time_threshold

        for i in range(max(0, index - 20), index):  # Look back up to 20 events
            prev_event = events[i]
            if prev_event.timestamp >= start_time:
                if prev_event.type in ["click", "type", "highlight", "copy", "paste"]:
                    activity_count += 1

        # If there was substantial activity before this page load, it's a break point
        return activity_count >= activity_threshold

    async def _get_segment_metadata(self, segment: List[BrowserEvent]) -> dict:
        """Extract metadata about a segment"""
        if not segment:
            return {}

        start_time = segment[0].timestamp
        end_time = segment[-1].timestamp
        duration = end_time - start_time

        domains = [event.domain for event in segment if event.domain]
        unique_domains = list(set(domains))

        event_types = [event.type for event in segment]
        unique_types = list(set(event_types))

        return {
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": duration,
            "event_count": len(segment),
            "domains": unique_domains,
            "event_types": unique_types,
            "primary_domain": unique_domains[0] if unique_domains else None,
        }
