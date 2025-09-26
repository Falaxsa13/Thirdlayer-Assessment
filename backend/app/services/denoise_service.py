from typing import List
from loguru import logger

from app.schemas.browser_events import BrowserEvent


class DenoiseService:
    """Service for denoising browser events to remove noise and accidental interactions"""

    def __init__(self):
        # Configuration parameters for denoising
        self.rapid_click_threshold_ms = 200  # Events within 200ms are considered rapid
        self.transient_tab_switch_threshold_ms = 2000  # Tab switches under 2 seconds are transient
        self.accidental_event_threshold_ms = 100  # Events under 100ms are likely accidental
        self.max_consecutive_same_element_clicks = 3  # Max clicks on same element before considering noise

    async def denoise_events(self, events: List[BrowserEvent]) -> List[BrowserEvent]:
        """Main denoising method that removes noise and accidental interactions from event stream"""
        if not events:
            return events

        logger.info(f"Starting denoising for {len(events)} events")

        # Sort events by timestamp to ensure proper order
        sorted_events = sorted(events, key=lambda x: x.timestamp)

        # Apply denoising filters
        denoised_events = await self._remove_rapid_clicks(sorted_events)
        denoised_events = await self._remove_transient_tab_switches(denoised_events)
        denoised_events = await self._remove_accidental_events(denoised_events)
        denoised_events = await self._remove_consecutive_same_element_clicks(denoised_events)
        denoised_events = await self._remove_focus_blur_noise(denoised_events)

        logger.info(f"Denoising complete: {len(denoised_events)} events remaining from {len(sorted_events)}")
        return denoised_events

    async def _remove_rapid_clicks(self, events: List[BrowserEvent]) -> List[BrowserEvent]:
        """Remove rapid clicks on the same element"""
        if len(events) < 2:
            return events

        denoised = []
        i = 0

        while i < len(events):
            current_event = events[i]

            # Check if this is a rapid click
            if self._is_rapid_click(current_event, events, i):
                logger.debug(f"Removing rapid click: {current_event.type} at {current_event.timestamp}")
                i += 1
                continue

            denoised.append(current_event)
            i += 1

        return denoised

    async def _remove_transient_tab_switches(self, events: List[BrowserEvent]) -> List[BrowserEvent]:
        """Remove transient tab switches (very short duration)"""
        if len(events) < 2:
            return events

        denoised = []
        i = 0

        while i < len(events):
            current_event = events[i]

            # Check if this is a transient tab switch
            if self._is_transient_tab_switch(current_event, events, i):
                logger.debug(f"Removing transient tab switch: {current_event.type} at {current_event.timestamp}")
                i += 1
                continue

            denoised.append(current_event)
            i += 1

        return denoised

    async def _remove_accidental_events(self, events: List[BrowserEvent]) -> List[BrowserEvent]:
        """Remove accidental events (very short duration interactions)"""
        if len(events) < 2:
            return events

        denoised = []
        i = 0

        while i < len(events):
            current_event = events[i]

            # Check if this is an accidental event
            if self._is_accidental_event(current_event, events, i):
                logger.debug(f"Removing accidental event: {current_event.type} at {current_event.timestamp}")
                i += 1
                continue

            denoised.append(current_event)
            i += 1

        return denoised

    async def _remove_consecutive_same_element_clicks(self, events: List[BrowserEvent]) -> List[BrowserEvent]:
        """Remove excessive consecutive clicks on the same element"""
        if len(events) < 2:
            return events

        denoised = []
        i = 0

        while i < len(events):
            current_event = events[i]

            # Check if this is excessive consecutive clicking
            if self._is_excessive_consecutive_clicking(current_event, events, i):
                logger.debug(f"Removing excessive consecutive click: {current_event.type} at {current_event.timestamp}")
                i += 1
                continue

            denoised.append(current_event)
            i += 1

        return denoised

    async def _remove_focus_blur_noise(self, events: List[BrowserEvent]) -> List[BrowserEvent]:
        """Remove focus/blur noise events"""
        if len(events) < 2:
            return events

        denoised = []
        i = 0

        while i < len(events):
            current_event = events[i]

            # Check if this is focus/blur noise
            if self._is_focus_blur_noise(current_event, events, i):
                logger.debug(f"Removing focus/blur noise: {current_event.type} at {current_event.timestamp}")
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

        # Check if previous event was also a click on the same element
        if previous_event.type != "click":
            return False

        # Check time gap
        time_gap = event.timestamp - previous_event.timestamp
        if time_gap > self.rapid_click_threshold_ms:
            return False

        # Check if it's the same element
        if self._is_same_element(event, previous_event):
            return True

        return False

    def _is_transient_tab_switch(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if this is a transient tab switch"""
        if event.type != "tab-switch":
            return False

        # Look ahead to see if user switches back quickly
        for i in range(index + 1, min(index + 5, len(events))):
            next_event = events[i]
            if next_event.type == "tab-switch":
                time_gap = next_event.timestamp - event.timestamp
                if time_gap < self.transient_tab_switch_threshold_ms:
                    return True

        return False

    def _is_accidental_event(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if this is an accidental event"""
        if index == 0:
            return False

        previous_event = events[index - 1]
        time_gap = event.timestamp - previous_event.timestamp

        # Very short duration events are likely accidental
        if time_gap < self.accidental_event_threshold_ms:
            return True

        return False

    def _is_excessive_consecutive_clicking(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if this is excessive consecutive clicking on the same element"""
        if event.type != "click":
            return False

        # Count consecutive clicks on the same element
        consecutive_count = 1
        for i in range(index - 1, max(0, index - 10), -1):
            prev_event = events[i]
            if prev_event.type == "click" and self._is_same_element(event, prev_event):
                consecutive_count += 1
            else:
                break

        return consecutive_count > self.max_consecutive_same_element_clicks

    def _is_focus_blur_noise(self, event: BrowserEvent, events: List[BrowserEvent], index: int) -> bool:
        """Check if this is focus/blur noise"""
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

    def _is_same_element(self, event1: BrowserEvent, event2: BrowserEvent) -> bool:
        """Check if two events involve the same DOM element"""
        if not event1.payload or not event2.payload:
            return False

        payload1 = event1.payload
        payload2 = event2.payload

        # Compare element information
        if payload1.element and payload2.element:
            elem1 = payload1.element
            elem2 = payload2.element

            # Compare by ID first (most reliable)
            if elem1.id and elem2.id and elem1.id == elem2.id:
                return True

            # Compare by tag + class combination
            if (
                elem1.tag == elem2.tag
                and elem1.class_name
                and elem2.class_name
                and elem1.class_name == elem2.class_name
            ):
                return True

        return False
