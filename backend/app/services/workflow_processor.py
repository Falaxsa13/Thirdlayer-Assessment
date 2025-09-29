from typing import List, Optional
from loguru import logger
from app.schemas.browser_events import BrowserEvent
from app.schemas.page_sessions import PageSession, PageSegment
from app.schemas.workflows import WorkflowSchema
from app.schemas.tools import ToolsCatalog
from app.services.segmentation.event_segmentation import EventSegmentationService
from app.services.generalization_service import GeneralizationService
from app.services.workflow_validator import WorkflowValidator
from app.services.workflow_exporter import WorkflowExporter
from app.services.tool_loader import ToolLoader
from app.services.workflow_deduplicator import WorkflowDeduplicator


class WorkflowProcessor:
    """Service for processing browser events and generating workflows"""

    def __init__(self):
        self.segmentation_service = EventSegmentationService()
        self.generalization_service = GeneralizationService()
        self.tool_loader = ToolLoader()
        self.workflow_exporter = WorkflowExporter()
        self.deduplicator = WorkflowDeduplicator()

    async def process_events_for_workflows(self, events: List[BrowserEvent]) -> List[WorkflowSchema]:
        """Hierarchical workflow processing: events -> candidate workflows -> workflows"""

        # Step 1: Segment events into candidate workflows (multi-page segments)
        candidate_workflows: List[PageSegment] = await self.segmentation_service.generate_candidate_workflows(events)

        # Step 2: Generalize page segments into workflows
        workflows: List[WorkflowSchema] = []

        for candidate_workflow in candidate_workflows:
            # Load tools based on segment's tool categories
            tools_catalog = self.tool_loader.load_tools_by_categories(candidate_workflow.tool_categories)
            workflow: Optional[WorkflowSchema] = await self.generalization_service.generalize_workflow(
                candidate_workflow, tools_catalog
            )
            if workflow:
                workflows.append(workflow)

        # Step 3: Validate and filter workflows (load all tools for validation)
        validated_workflows: List[WorkflowSchema] = self._validate_workflows(workflows)
        unique_workflows: List[WorkflowSchema] = await self.deduplicator.deduplicate_workflows(validated_workflows)

        # Step 4: Export workflows to organized folder structure
        if unique_workflows:
            self.workflow_exporter.export_workflows(unique_workflows)

        return unique_workflows

    def _validate_workflows(self, workflows: List[WorkflowSchema]) -> List[WorkflowSchema]:
        """Validate workflows and filter out invalid ones"""
        validator = WorkflowValidator()
        valid_workflows = []

        for workflow in workflows:
            is_valid, error = validator.validate_workflow(workflow)
            if is_valid:
                valid_workflows.append(workflow)
                logger.info(f"✅ Valid workflow: {workflow.summary}")
            else:
                logger.warning(f"❌ Invalid workflow rejected: {error}")

        return valid_workflows
