from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean, Float
from sqlalchemy.sql import func
from app.core.database import Base


class Workflow(Base):
    """Database model for storing generated workflows"""

    __tablename__ = "workflows"

    id = Column(String, primary_key=True, index=True)
    summary = Column(Text, nullable=False)  # Natural language summary
    domain = Column(String, nullable=True, index=True)  # Domain pattern for grouping
    url_pattern = Column(String, nullable=True)  # URL pattern for grouping

    # Workflow metadata
    confidence_score = Column(Float, default=0.0)  # LLM confidence score
    is_active = Column(Boolean, default=True)  # Whether workflow is active
    execution_count = Column(Integer, default=0)  # How many times executed

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_executed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Workflow(id={self.id}, summary={self.summary[:50]}...)>"


class WorkflowStep(Base):
    """Database model for storing individual workflow steps"""

    __tablename__ = "workflow_steps"

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, nullable=False, index=True)  # Foreign key to workflows
    step_order = Column(Integer, nullable=False)  # Order within workflow

    # Step content
    description = Column(Text, nullable=False)  # Human-readable description
    step_type = Column(String, nullable=False)  # "browser_context" or "tool"

    # Tool-specific fields (when step_type = "tool")
    tools = Column(JSON, nullable=True)  # List of tool names
    tool_parameters = Column(JSON, nullable=True)  # Tool parameters

    # Browser context fields (when step_type = "browser_context")
    context_selector = Column(String, nullable=True)  # CSS selector
    context_description = Column(Text, nullable=True)  # What to extract

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<WorkflowStep(id={self.id}, workflow_id={self.workflow_id}, order={self.step_order})>"


class WorkflowExecution(Base):
    """Database model for tracking workflow executions"""

    __tablename__ = "workflow_executions"

    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, nullable=False, index=True)

    # Execution details
    status = Column(String, nullable=False)  # "pending", "running", "completed", "failed"
    input_data = Column(JSON, nullable=True)  # Input context data
    output_data = Column(JSON, nullable=True)  # Execution results

    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"
