from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger
from app.core.database import get_db
from app.schemas.events import EventBatchRequest, EventBatchResponse
from app.services.workflow_processor import WorkflowProcessor
from app.schemas.workflows import WorkflowSchema
from typing import List

router = APIRouter()


@router.post("/interactions", response_model=EventBatchResponse)
async def receive_events(request: EventBatchRequest, db: Session = Depends(get_db)):
    """Will receive batches of interaction events and store them in the database"""
    try:
        # Generate workflows from the processed events
        workflow_processor = WorkflowProcessor(db)
        workflows: List[WorkflowSchema] = await workflow_processor.process_events_for_workflows(request.events)

        # Save workflows
        if workflows:
            saved_ids = await workflow_processor.save_workflows(workflows)
            logger.info(f"Generated and saved {len(saved_ids)} workflows")

        return EventBatchResponse(
            success=True,
            message=f"Successfully processed all events and generated {len(workflows)} workflows",
        )

    except Exception as e:
        logger.error(f"Error processing event batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}"
        )
