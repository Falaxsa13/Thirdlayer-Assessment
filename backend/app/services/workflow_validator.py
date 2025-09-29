from typing import List
from loguru import logger
from app.schemas.workflows import WorkflowSchema, WorkflowStepSchema
from app.services.tool_loader import ToolLoader


class WorkflowValidator:
    """Validates workflows against available tools and constraints"""

    def __init__(self):
        self.tool_loader = ToolLoader()
        self.valid_step_types = {"browser_context", "tool"}

    def validate_workflow(self, workflow: WorkflowSchema) -> tuple[bool, str]:
        """Validate workflow and return (is_valid, error_message)"""

        # Check tool availability
        available_tools = self.tool_loader.load_all_tools()
        available_tool_names = {tool.name for tool in available_tools.tools}

        for step in workflow.steps:
            if step.step_type == "tool":
                for tool in step.tools or []:
                    if tool not in available_tool_names:
                        return False, f"Tool '{tool}' not available"

        # Check step validity
        if not self._has_valid_steps(workflow.steps):
            return False, "Invalid workflow steps"

        return True, ""

    def _has_valid_steps(self, steps: List[WorkflowStepSchema]) -> bool:
        """Check if workflow has valid steps"""
        if len(steps) < 2:
            return False

        # First step must be browser_context
        if steps[0].step_type != "browser_context":
            return False

        # All steps must have valid types
        for step in steps:
            if step.step_type not in self.valid_step_types:
                return False

        return True
