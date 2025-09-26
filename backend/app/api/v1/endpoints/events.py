from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger
from app.schemas.tools import ToolsCatalog
from datetime import datetime
from app.core.database import get_db
from app.schemas.events import EventBatchRequest, EventBatchResponse
from app.services.event_processor import EventProcessor
from app.services.workflow_processor import WorkflowProcessor

router = APIRouter()


@router.post("/interactions", response_model=EventBatchResponse)
async def receive_events(request: EventBatchRequest, db: Session = Depends(get_db)):
    """Will receive batches of interaction events and store them in the database"""
    try:
        # Process events and store them
        processor = EventProcessor(db)
        result = await processor.process_events(request.events)

        # This line is a placeholder for the tools catalog
        empty_tools_catalog = ToolsCatalog(
            tools=[], last_updated=int(datetime.now().timestamp() * 1000), version="1.0.0"
        )

        # Generate workflows from the events
        workflow_processor = WorkflowProcessor(db)
        workflows = await workflow_processor.process_events_for_workflows(request.events, empty_tools_catalog)

        # Save workflows
        if workflows:
            saved_ids = await workflow_processor.save_workflows(workflows)
            logger.info(f"Generated and saved {len(saved_ids)} workflows")

        return EventBatchResponse(
            success=True,
            processed_count=result.processed_count,
            message=f"Successfully processed {result.processed_count} events and generated {len(workflows)} workflows",
        )

    except Exception as e:
        logger.error(f"Error processing event batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}"
        )


@router.get("/interactions")
async def get_events(limit: int = 100, db: Session = Depends(get_db)):
    """
    TODO: Retrieve interaction events from the database

    Args:
        limit: Maximum number of events to return (default: 100)
    """
    try:
        # TODO: Implement event retrieval logic
        logger.info(f"TODO: Retrieving {limit} events")

        return {"message": "TODO: Implement event retrieval", "limit": limit, "events": []}

    except Exception as e:
        logger.error(f"Error retrieving events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}"
        )
