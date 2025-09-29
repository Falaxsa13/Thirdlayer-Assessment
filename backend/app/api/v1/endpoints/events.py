from fastapi import APIRouter, HTTPException, status
from loguru import logger
from app.schemas.events import EventBatchRequest, EventBatchResponse
from app.services.workflow_processor import WorkflowProcessor
from app.schemas.workflows import WorkflowSchema
from typing import List

router = APIRouter()


@router.post("/interactions", response_model=EventBatchResponse)
async def receive_events(request: EventBatchRequest):
    """Process interaction events and generate workflows (stored as JSON files)"""
    try:
        # Generate workflows from the processed events
        workflow_processor = WorkflowProcessor()
        workflows: List[WorkflowSchema] = await workflow_processor.process_events_for_workflows(request.events)

        return EventBatchResponse(
            success=True,
            message=f"Successfully processed all events and generated {len(workflows)} workflows",
        )

    except Exception as e:
        logger.error(f"Error processing event batch: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error")
