from typing import List, Optional
from sqlalchemy.orm import Session
from loguru import logger
import uuid
from datetime import datetime

from app.models.workflows import Workflow, WorkflowStep
from app.schemas.browser_events import BrowserEvent, EventSegment
from app.schemas.tools import ToolsCatalog
from app.schemas.workflows import WorkflowSchema, WorkflowStepSchema
from app.services.event_segmentation import EventSegmentationService


class WorkflowProcessor:
    """Service for processing browser events and generating workflows"""

    def __init__(self, db: Session):
        self.db = db
        self.segmentation_service = EventSegmentationService()

    async def process_events_for_workflows(
        self, events: List[BrowserEvent], tools_catalog: ToolsCatalog
    ) -> List[WorkflowSchema]:
        """
        TODO: Main workflow generation pipeline

        This is the core method that will:
        1. Segment events into candidate workflows
        2. Generalize workflows (remove instance-specific details)
        3. Denoise (remove accidental clicks, noise)
        4. Group/deduplicate similar workflows
        5. Filter workflows that can't be executed with available tools

        Args:
            events: List of browser interaction events
            tools_catalog: Available tools and integrations

        Returns:
            List of generated workflows
        """
        logger.info(f"Starting workflow processing for {len(events)} events")

        # Step 1: Segment events into candidate workflows
        segments = await self.segmentation_service.segment_events(events)
        logger.info(f"Segmented events into {len(segments)} candidate workflows")

        # Log segmentation results
        for i, segment in enumerate(segments):
            logger.info(
                f"Segment {i+1}: {segment.segment_type} - {len(segment.events)} events, "
                f"duration: {segment.duration_ms}ms, confidence: {segment.confidence_score:.2f}"
            )
            logger.info(f"  Events: {segment.event_types}")
            if segment.domain:
                logger.info(f"  Domain: {segment.domain}")

        # Step 2: Convert segments to workflows
        workflows = []
        for segment in segments:
            if segment.confidence_score < 0.3:  # Skip low-confidence segments
                continue

            workflow = await self._segment_to_workflow(segment, tools_catalog)
            if workflow:
                workflows.append(workflow)

        logger.info(f"Generated {len(workflows)} workflows from {len(segments)} segments")
        return workflows

    async def save_workflows(self, workflows: List[WorkflowSchema]) -> List[str]:
        """
        Save workflows to the database

        Args:
            workflows: List of workflows to save

        Returns:
            List of saved workflow IDs
        """
        saved_ids = []

        for workflow in workflows:
            try:
                # Create workflow record
                workflow_id = str(uuid.uuid4())
                db_workflow = Workflow(
                    id=workflow_id,
                    summary=workflow.summary,
                    domain=workflow.domain,
                    url_pattern=workflow.url_pattern,
                    confidence_score=workflow.confidence_score,
                    is_active=workflow.is_active,
                    execution_count=workflow.execution_count or 0,
                )

                self.db.add(db_workflow)

                # Create workflow steps
                for i, step in enumerate(workflow.steps):
                    step_id = str(uuid.uuid4())
                    db_step = WorkflowStep(
                        id=step_id,
                        workflow_id=workflow_id,
                        step_order=i,
                        description=step.description,
                        step_type=step.step_type,
                        tools=step.tools,
                        tool_parameters=step.tool_parameters,
                        context_selector=step.context_selector,
                        context_description=step.context_description,
                    )

                    self.db.add(db_step)

                saved_ids.append(workflow_id)
                logger.info(f"Saved workflow: {workflow_id}")

            except Exception as e:
                logger.error(f"Failed to save workflow: {str(e)}")
                continue

        try:
            self.db.commit()
            logger.info(f"Successfully saved {len(saved_ids)} workflows")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit workflows: {str(e)}")
            saved_ids = []

        return saved_ids

    async def _segment_to_workflow(
        self, segment: EventSegment, tools_catalog: ToolsCatalog
    ) -> Optional[WorkflowSchema]:
        """Convert an event segment to a workflow schema"""
        try:
            # Generate workflow summary based on segment type
            summary = await self._generate_workflow_summary(segment)

            # Generate workflow steps based on events
            steps = await self._generate_workflow_steps(segment, tools_catalog)

            if not steps:
                return None

            # Extract URL pattern
            url_pattern = await self._extract_url_pattern(segment)

            workflow = WorkflowSchema(
                id=str(uuid.uuid4()),
                summary=summary,
                steps=steps,
                domain=segment.domain,
                url_pattern=url_pattern,
                confidence_score=segment.confidence_score,
                is_active=True,
                execution_count=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            return workflow

        except Exception as e:
            logger.error(f"Failed to convert segment to workflow: {str(e)}")
            return None

    async def _generate_workflow_summary(self, segment: EventSegment) -> str:
        """Generate a natural language summary for the workflow"""
        segment_type = segment.segment_type
        event_count = len(segment.events)
        duration_minutes = segment.duration_ms / 60000

        if segment_type == "form_filling":
            return f"Fill out form with {event_count} interactions over {duration_minutes:.1f} minutes"
        elif segment_type == "navigation":
            return f"Navigate through {event_count} pages over {duration_minutes:.1f} minutes"
        elif segment_type == "content_interaction":
            return f"Interact with content ({event_count} actions) over {duration_minutes:.1f} minutes"
        elif segment_type == "search":
            return f"Search and browse results ({event_count} actions) over {duration_minutes:.1f} minutes"
        elif segment_type == "page_session":
            return f"Browse page with {event_count} interactions over {duration_minutes:.1f} minutes"
        else:
            return f"User activity with {event_count} interactions over {duration_minutes:.1f} minutes"

    async def _generate_workflow_steps(
        self, segment: EventSegment, tools_catalog: ToolsCatalog
    ) -> List[WorkflowStepSchema]:
        """Generate workflow steps based on segment events"""
        steps = []

        # Add browser context step
        steps.append(
            WorkflowStepSchema(
                description=f"Extract information from {segment.segment_type} session",
                step_type="browser_context",
                tools=None,
                tool_parameters=None,
                context_selector=None,
                context_description=f"Process {len(segment.events)} events of types: {', '.join(set(segment.event_types))}",
            )
        )

        # Add tool steps based on segment type
        if segment.segment_type == "form_filling":
            steps.append(
                WorkflowStepSchema(
                    description="Process form data and save to appropriate system",
                    step_type="tool",
                    tools=["google-sheets-add-rows", "hubspot-add-contact"],
                    tool_parameters=None,
                    context_selector=None,
                    context_description=None,
                )
            )
        elif segment.segment_type == "content_interaction":
            steps.append(
                WorkflowStepSchema(
                    description="Save highlighted content to knowledge base",
                    step_type="tool",
                    tools=["notion-add-page", "google-docs-create"],
                    tool_parameters=None,
                    context_selector=None,
                    context_description=None,
                )
            )
        elif segment.segment_type == "search":
            steps.append(
                WorkflowStepSchema(
                    description="Save search results and insights",
                    step_type="tool",
                    tools=["google-sheets-add-rows", "notion-add-page"],
                    tool_parameters=None,
                    context_selector=None,
                    context_description=None,
                )
            )
        else:
            # Generic tool step
            steps.append(
                WorkflowStepSchema(
                    description="Process and save the collected information",
                    step_type="tool",
                    tools=["google-sheets-add-rows"],
                    tool_parameters=None,
                    context_selector=None,
                    context_description=None,
                )
            )

        return steps

    async def _extract_url_pattern(self, segment: EventSegment) -> Optional[str]:
        """Extract URL pattern from segment events"""
        urls = [event.url for event in segment.events if event.url]
        if not urls:
            return None

        # Use the most common domain
        domains = [event.domain for event in segment.events if event.domain]
        if domains:
            from collections import Counter

            most_common_domain = Counter(domains).most_common(1)[0][0]
            return f"*://{most_common_domain}/*"

        return None

    def _extract_domain(self, url: str) -> Optional[str]:
        """Extract domain from URL"""
        if not url:
            return None

        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return None
