from typing import List, Dict, Optional, Any
from loguru import logger
import json

from app.schemas.browser_events import BrowserEvent, EventSegment
from app.core.config import settings
from app.services.utils import load_prompt
from openai import OpenAI


class IntentClassificationService:
    """Service for classifying event segments using LLM analysis"""

    def __init__(self):
        # Initialize OpenAI client
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.llm_available = bool(settings.openai_api_key)

    async def classify_segment_intent(self, segment: EventSegment) -> str:
        """
        Classifies the primary intent of a given event segment using LLM analysis.

        Args:
            segment: EventSegment to classify

        Returns:
            Classified intent as a string
        """
        if not self.llm_available:
            logger.warning("LLM not available for intent classification - using fallback")
            return "unknown"

        try:
            # Extract context for LLM analysis
            page_content = await self._extract_page_content(segment)
            user_actions = await self._extract_user_actions(segment)

            # Use LLM to classify intent
            intent = await self._classify_intent_with_llm(
                segment=segment, page_content=page_content, user_actions=user_actions
            )

            logger.debug(f"LLM classified segment as: {intent}")
            return intent

        except Exception as e:
            logger.error(f"Failed to classify segment intent with LLM: {str(e)}")
            return "unknown"

    async def _extract_page_content(self, segment: EventSegment) -> str:
        """Extract relevant page content from segment events"""
        content_parts = []

        for event in segment.events:
            if event.payload and event.payload.markdown:
                # Truncate very long markdown content
                markdown = event.payload.markdown
                if len(markdown) > 500:
                    markdown = markdown[:500] + "..."
                content_parts.append(f"Page: {event.title}\nContent: {markdown}")

            if event.payload and event.payload.text:
                content_parts.append(f"User input: {event.payload.text}")

        return "\n\n".join(content_parts) if content_parts else "No page content available"

    async def _extract_user_actions(self, segment: EventSegment) -> str:
        """Extract user actions summary from segment events"""
        actions = []

        for event in segment.events:
            if event.type == "click" and event.payload and event.payload.element:
                element = event.payload.element
                action_desc = f"Clicked on {element.tag}"
                if element.text:
                    action_desc += f" with text '{element.text}'"
                elif element.id:
                    action_desc += f" with id '{element.id}'"
                actions.append(action_desc)

            elif event.type == "type" and event.payload and event.payload.text:
                actions.append(f"Typed: '{event.payload.text}'")

            elif event.type == "page-load":
                actions.append(f"Loaded page: {event.title}")

            elif event.type == "highlight":
                actions.append(f"Highlighted text")

        return "; ".join(actions) if actions else "No specific actions detected"

    async def _classify_intent_with_llm(self, segment: EventSegment, page_content: str, user_actions: str) -> str:
        """Classify intent using LLM analysis"""

        # Load prompt from file
        prompt = load_prompt(
            "intent_classification.txt",
            variables={
                "domain": segment.domain,
                "duration_ms": segment.duration_ms,
                "event_types": segment.event_types,
                "page_content": page_content,
                "user_actions": user_actions,
            },
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing user behavior and classifying their intent. Be precise and choose the most specific category that matches the user's primary goal.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=50,  # Short response expected
            )

            if not response.choices[0].message.content:
                return "unknown"

            intent = response.choices[0].message.content.strip().lower()

            return intent

        except Exception as e:
            logger.error(f"OpenAI API call failed for intent classification: {str(e)}")
            return "unknown"
