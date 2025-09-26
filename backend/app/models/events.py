from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class BrowserEventDBModel(Base):
    """Database model for storing interaction events from Chrome extension"""

    __tablename__ = "browser_events"

    # Primary fields
    id = Column(String, primary_key=True, index=True)
    type = Column(String, nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)

    # Optional fields (can be null)
    tab_id = Column(Integer, nullable=True, index=True)
    window_id = Column(Integer, nullable=True, index=True)
    url = Column(Text, nullable=True, index=True)
    title = Column(Text, nullable=True)

    # Payload as JSON (contains element, text, markdown, etc.)
    payload = Column(JSON, nullable=True)

    # Computed fields for easier querying
    domain = Column(String, nullable=True, index=True)
    is_page_load = Column(Boolean, nullable=False, default=False, index=True)
    is_click = Column(Boolean, nullable=False, default=False, index=True)
    is_type = Column(Boolean, nullable=False, default=False, index=True)
    is_highlight = Column(Boolean, nullable=False, default=False, index=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
