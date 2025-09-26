from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

from app.schemas.browser_events import BrowserEvent
from app.schemas.tools import ToolsCatalog


class WorkflowStepSchema(BaseModel):
    """Schema for individual workflow steps"""

    description: str = Field(..., description="Human-readable description of the step")
    step_type: Literal["browser_context", "tool"] = Field(..., description="Type of step")
    tools: Optional[List[str]] = Field(None, description="List of tool names (for tool steps)")
    tool_parameters: Optional[Dict[str, Any]] = Field(None, description="Tool parameters")
    context_selector: Optional[str] = Field(None, description="CSS selector (for browser_context steps)")
    context_description: Optional[str] = Field(None, description="What to extract (for browser_context steps)")


class WorkflowSchema(BaseModel):
    """Schema for complete workflows"""

    id: Optional[str] = Field(None, description="Workflow ID")
    summary: str = Field(..., description="Natural language summary of the workflow")
    steps: List[WorkflowStepSchema] = Field(..., description="Ordered list of workflow steps")
    domain: Optional[str] = Field(None, description="Domain pattern for grouping")
    url_pattern: Optional[str] = Field(None, description="URL pattern for grouping")
    confidence_score: Optional[float] = Field(0.0, description="LLM confidence score")
    is_active: Optional[bool] = Field(True, description="Whether workflow is active")
    execution_count: Optional[int] = Field(0, description="How many times executed")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class WorkflowGenerationRequest(BaseModel):
    """Request schema for workflow generation"""

    events: List[BrowserEvent] = Field(..., description="List of browser interaction events")
    tools_catalog: ToolsCatalog = Field(..., description="Available tools and integrations")
    time_window_hours: Optional[int] = Field(1, description="Time window in hours")


class WorkflowGenerationResponse(BaseModel):
    """Response schema for workflow generation"""

    success: bool = Field(..., description="Whether generation was successful")
    workflows_generated: int = Field(..., description="Number of workflows generated")
    workflows: List[WorkflowSchema] = Field(..., description="Generated workflows")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")
    message: Optional[str] = Field(None, description="Response message")


class WorkflowExecutionRequest(BaseModel):
    """Request schema for workflow execution"""

    workflow_id: str = Field(..., description="ID of workflow to execute")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Browser context data")


class WorkflowExecutionResponse(BaseModel):
    """Response schema for workflow execution"""

    success: bool = Field(..., description="Whether execution was successful")
    execution_id: str = Field(..., description="Execution ID")
    status: str = Field(..., description="Execution status")
    results: Optional[Dict[str, Any]] = Field(None, description="Execution results")
    message: Optional[str] = Field(None, description="Response message")
