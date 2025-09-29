from typing import List, Dict, Optional, Any, Tuple
from loguru import logger
import json
from app.schemas.page_sessions import PageSession
from app.core.config import settings
from app.services.utils import load_prompt
from openai import OpenAI
from app.services.tool_loader import ToolLoader


class IntentClassificationService:
    """Service for classifying event segments using LLM analysis"""

    def __init__(self):
        # Initialize OpenAI client
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.llm_available = bool(settings.openai_api_key)
        self.tool_loader = ToolLoader()

    def _parse_intent_response(self, response_text: str) -> Tuple[str, List[str]]:
        """Parse LLM response to extract intent and tool categories"""
        try:
            # Handle JSON response
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            response_data = json.loads(response_text)

            intent = response_data.get("intent", "unknown").lower()
            tool_categories = response_data.get("tool_categories", [])

            return intent, tool_categories

        except json.JSONDecodeError:
            # Fallback: try to parse as simple text
            lines = response_text.strip().split("\n")
            intent = "unknown"
            tool_categories = []

            for line in lines:
                if line.lower().startswith("intent:"):
                    intent = line.split(":", 1)[1].strip().lower()
                elif line.lower().startswith("tool_categories:"):
                    categories_text = line.split(":", 1)[1].strip()
                    tool_categories = [cat.strip() for cat in categories_text.split(",") if cat.strip()]

            return intent, tool_categories

    async def classify_segment_intent(self, page_segment: List[PageSession]) -> Tuple[str, List[str]]:
        """Classify page segment intent and tool categories"""
        if not self.llm_available:
            return "unknown", []

        try:
            page_content = self._extract_page_content(page_segment)
            user_actions = self._extract_user_actions(page_segment)
            return await self._classify_intent_with_llm(page_segment, page_content, user_actions)
        except Exception as e:
            logger.error(f"Failed to classify page segment: {str(e)}")
            return "unknown", []

    def _extract_page_content(self, page_segment: List[PageSession]) -> str:
        """Extract page content from page sessions"""
        content_parts = []
        for page in page_segment:
            content_parts.append(f"Page: {page.title}\nContent: {page.content_summary}")
        return "\n\n".join(content_parts) if content_parts else "No page content available"

    def _extract_user_actions(self, page_segment: List[PageSession]) -> str:
        """Extract user actions from page sessions"""
        actions = []
        for page in page_segment:
            actions.append(f"Visited page: {page.title} for {page.duration_ms}ms")
        return "; ".join(actions) if actions else "No specific actions detected"

    async def _classify_intent_with_llm(
        self, page_segment: List[PageSession], page_content: str, user_actions: str
    ) -> Tuple[str, List[str]]:
        """Classify page segment using LLM"""
        tool_categories = self.tool_loader.get_available_tool_categories()
        representative_page = page_segment[0]

        prompt = load_prompt(
            "intent_classification.txt",
            variables={
                "domain": representative_page.domain,
                "duration_ms": sum(page.duration_ms for page in page_segment),
                "event_types": ["page-load"],
                "page_content": page_content,
                "user_actions": user_actions,
                "tool_categories": tool_categories,
            },
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing user behavior and classifying their intent.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            if not response.choices[0].message.content:
                return "unknown", []

            return self._parse_intent_response(response.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            return "unknown", []
