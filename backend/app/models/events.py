from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class InteractionEvent(Base):
    """TODO: Define database model for storing interaction events"""

    __tablename__ = "interaction_events"

    # TODO: Add proper columns based on Chrome extension event structure
    id = Column(String, primary_key=True, index=True)
    type = Column(String, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    # TODO: Add more columns as needed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
