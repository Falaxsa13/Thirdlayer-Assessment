from typing import List, Optional
from sqlalchemy.orm import Session
from loguru import logger
import uuid
from datetime import datetime
from app.models.workflows import Workflow, WorkflowStep
from app.schemas.browser_events import BrowserEvent, EventSegment
from app.schemas.tools import ToolsCatalog
from app.schemas.workflows import WorkflowSchema, WorkflowStepSchema
from app.services.segmentation.event_segmentation import EventSegmentationService
from app.services.denoise_service import DenoiseService
from app.services.generalization_service import GeneralizationService


class WorkflowProcessor:
    """Service for processing browser events and generating workflows"""

    def __init__(self, db: Session):
        self.db = db
        self.segmentation_service = EventSegmentationService()
        self.denoise_service = DenoiseService()
        self.generalization_service = GeneralizationService()

    async def process_events_for_workflows(
        self, events: List[BrowserEvent], tools: ToolsCatalog
    ) -> List[WorkflowSchema]:
        """This is the main method that processes events, generates workflows and saves them to the database"""

        # Step 1: Denoise events using dedicated service
        denoised_events = await self.denoise_service.denoise_events(events)
        logger.info(f"Denoised events: {len(denoised_events)} remaining from {len(events)}")

        # Step 2: Segment events into candidate workflows
        segments = await self.segmentation_service.segment_events(denoised_events)
        logger.info(f"Segments: {len(segments)} segments found")

        # Step 3: Generalize segments into workflows
        workflows = []
        for segment in segments:
            workflow = await self.generalization_service.generalize_workflow(segment, tools)
            if workflow:
                workflows.append(workflow)

        logger.info(f"Generated {len(workflows)} generalized workflows from {len(segments)} segments")
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
