from typing import List
from sqlalchemy.orm import Session
from loguru import logger
from app.models.events import BrowserEventDBModel
from app.schemas.browser_events import BrowserEvent
from app.schemas.events import EventBatchResponse


class EventProcessor:
    """Service for processing and storing browser interaction events"""

    def __init__(self, db: Session):
        self.db = db

    async def process_events(self, events: List[BrowserEvent]) -> EventBatchResponse:
        """Process a batch of events and store them in the database"""
        logger.info(f"Processing {len(events)} events")

        stored_count = 0

        try:
            for i, event in enumerate(events):
                logger.info(f"Processing event {i+1}/{len(events)}: {event.type} at {event.timestamp}")

                # Convert Pydantic model to database model
                db_event = BrowserEventDBModel(
                    id=event.id,
                    type=event.type,
                    timestamp=event.timestamp,
                    tab_id=event.tab_id,
                    window_id=event.window_id,
                    url=event.url,
                    title=event.title,
                    payload=event.payload.model_dump() if event.payload else None,
                    domain=event.domain,
                    is_page_load=event.is_page_load,
                    is_click=event.is_click,
                    is_type=event.is_type_event,
                    is_highlight=event.is_highlight,
                )

                # Add to session
                self.db.add(db_event)
                stored_count += 1

                logger.info(f"Added event to database: {event.type} at {event.timestamp}")

            # Commit all events at once
            self.db.commit()

            logger.info(f"Successfully stored {stored_count} events in database")

        except Exception as e:
            logger.error(f"Error processing events: {str(e)}")
            self.db.rollback()
            stored_count = 0

        return EventBatchResponse(
            success=stored_count > 0,
            processed_count=stored_count,
            message=f"Successfully stored {stored_count} events in database",
        )
