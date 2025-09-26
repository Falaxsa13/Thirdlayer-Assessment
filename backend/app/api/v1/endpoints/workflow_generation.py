from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger
import time
from datetime import datetime
from typing import Literal

from app.core.database import get_db
from app.schemas.workflows import (
    WorkflowGenerationRequest,
    WorkflowGenerationResponse,
    WorkflowSchema,
    WorkflowStepSchema,
)
from app.schemas.tools import ToolsCatalog
from app.services.workflow_processor import WorkflowProcessor

router = APIRouter()


@router.post("/generate", response_model=WorkflowGenerationResponse)
async def generate_workflows(request: WorkflowGenerationRequest, db: Session = Depends(get_db)):
    """
    Generate workflows from browser interaction events

    This endpoint processes a sequence of browser events and generates
    generalized workflows that can be executed using available tools.
    """
    start_time = time.time()

    try:
        logger.info(f"Starting workflow generation for {len(request.events)} events")

        # Initialize workflow processor
        processor = WorkflowProcessor(db)

        # Process events to generate workflows
        workflows = await processor.process_events_for_workflows(request.events, request.tools_catalog)

        # Save workflows to database
        saved_ids = await processor.save_workflows(workflows)

        processing_time = time.time() - start_time

        logger.info(f"Generated {len(workflows)} workflows in {processing_time:.2f} seconds")

        return WorkflowGenerationResponse(
            success=True,
            workflows_generated=len(workflows),
            workflows=workflows,
            processing_time_seconds=processing_time,
            message=f"Successfully generated {len(workflows)} workflows",
        )

    except Exception as e:
        logger.error(f"Error generating workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Workflow generation failed: {str(e)}"
        )


@router.get("/workflows", response_model=list[WorkflowSchema])
async def get_workflows(limit: int = 100, active_only: bool = True, db: Session = Depends(get_db)):
    """
    Retrieve stored workflows

    Args:
        limit: Maximum number of workflows to return
        active_only: Only return active workflows
    """
    try:
        from app.models.workflows import Workflow, WorkflowStep

        # Build query
        query = db.query(Workflow)
        if active_only:
            query = query.filter(Workflow.is_active == True)

        # Get workflows
        workflows = query.order_by(Workflow.created_at.desc()).limit(limit).all()

        # Convert to response format
        result = []
        for workflow in workflows:
            # Get workflow steps
            steps = (
                db.query(WorkflowStep)
                .filter(WorkflowStep.workflow_id == workflow.id)
                .order_by(WorkflowStep.step_order)
                .all()
            )

            # Convert steps to schema
            step_schemas = []
            for step in steps:
                step_schemas.append(
                    WorkflowStepSchema(
                        description=step.description,  # type: ignore
                        step_type=step.step_type,  # type: ignore
                        tools=step.tools,  # type: ignore
                        tool_parameters=step.tool_parameters,  # type: ignore
                        context_selector=step.context_selector,  # type: ignore
                        context_description=step.context_description,  # type: ignore
                    )
                )

            # Create workflow schema
            workflow_schema = WorkflowSchema(
                id=str(workflow.id),
                summary=str(workflow.summary),
                steps=step_schemas,
                domain=str(workflow.domain),
                url_pattern=str(workflow.url_pattern),
                confidence_score=workflow.confidence_score,  # type: ignore
                is_active=bool(workflow.is_active),
                execution_count=workflow.execution_count,  # type: ignore
                created_at=workflow.created_at,  # type: ignore
                updated_at=workflow.updated_at,  # type: ignore
            )

            result.append(workflow_schema)

        logger.info(f"Retrieved {len(result)} workflows")
        return result

    except Exception as e:
        logger.error(f"Error retrieving workflows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve workflows: {str(e)}"
        )
