import json
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger

from app.schemas.workflows import WorkflowSchema


class WorkflowExporter:
    """Service for exporting workflows to organized folder structure"""

    def __init__(self, output_dir: str = "workflows"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"Workflow exporter initialized with output directory: {self.output_dir}")

    def export_workflows(self, workflows: List[WorkflowSchema]) -> List[str]:
        """Export workflows to single folder with individual JSON files"""
        if not workflows:
            logger.warning("No workflows to export")
            return []

        logger.info(f"Exporting {len(workflows)} workflows to {self.output_dir}")

        exported_files = []

        for i, workflow in enumerate(workflows):
            # Create workflow file directly in the main folder
            workflow_file = self._create_workflow_file(workflow, self.output_dir, i + 1)
            exported_files.append(str(workflow_file))

        logger.info(f"Successfully exported {len(exported_files)} workflow files")
        return exported_files

    def _sanitize_folder_name(self, name: str) -> str:
        """Sanitize folder name to be filesystem-safe"""
        # Replace invalid characters with underscores
        sanitized = "".join(c if c.isalnum() or c in ".-_" else "_" for c in name)
        # Remove multiple underscores
        sanitized = "_".join(part for part in sanitized.split("_") if part)
        return sanitized or "unknown"

    def _create_workflow_file(self, workflow: WorkflowSchema, output_folder: Path, index: int) -> Path:
        """Create a single workflow file with all necessary information"""

        # Create workflow data structure
        workflow_data = {
            "metadata": {
                "id": workflow.id,
                "summary": workflow.summary,
                "domain": workflow.domain,
                "url_pattern": workflow.url_pattern,
                "created_at": datetime.now().isoformat(),
                "step_count": len(workflow.steps),
                "has_tools": any(step.tools for step in workflow.steps),
                "tool_count": sum(len(step.tools or []) for step in workflow.steps),
            },
            "workflow": {
                "summary": workflow.summary,
                "domain": workflow.domain,
                "url_pattern": workflow.url_pattern,
                "steps": [],
            },
            "analysis": {
                "intent_classification": "unknown",
                "complexity_score": self._calculate_complexity_score(workflow),
                "tool_usage": self._analyze_tool_usage(workflow),
                "browser_context_usage": self._analyze_browser_context_usage(workflow),
            },
        }

        # Add steps with detailed information
        for i, step in enumerate(workflow.steps):
            step_data = {
                "step_number": i + 1,
                "description": step.description,
                "step_type": step.step_type,
                "context_description": step.context_description,
            }

            if step.step_type == "tool" and step.tools:
                step_data["tools"] = {
                    "tool_names": step.tools,
                    "tool_count": len(step.tools),
                    "tool_details": self._get_tool_details(step.tools),
                }

            if step.step_type == "browser_context":
                step_data["browser_context"] = {
                    "context_selector": step.context_selector,
                    "context_description": step.context_description,
                }

            workflow_data["workflow"]["steps"].append(step_data)

        # Create filename
        safe_summary = self._sanitize_folder_name(workflow.summary)[:50]
        filename = f"{index:02d}_{safe_summary}.json"
        file_path = output_folder / filename

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(workflow_data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Created workflow file: {file_path}")
        return file_path

    def _calculate_complexity_score(self, workflow: WorkflowSchema) -> int:
        """Calculate workflow complexity score"""
        score = len(workflow.steps)  # Base score from step count
        score += sum(len(step.tools or []) for step in workflow.steps)  # Add tool count
        return score

    def _analyze_tool_usage(self, workflow: WorkflowSchema) -> Dict[str, Any]:
        """Analyze tool usage in workflow"""
        all_tools = []
        for step in workflow.steps:
            if step.tools:
                all_tools.extend(step.tools)

        return {
            "total_tools": len(all_tools),
            "unique_tools": len(set(all_tools)),
            "tool_names": list(set(all_tools)),
            "tool_steps": len([s for s in workflow.steps if s.tools]),
        }

    def _analyze_browser_context_usage(self, workflow: WorkflowSchema) -> Dict[str, Any]:
        """Analyze browser context usage in workflow"""
        browser_steps = [s for s in workflow.steps if s.step_type == "browser_context"]

        return {
            "browser_context_steps": len(browser_steps),
            "total_steps": len(workflow.steps),
            "browser_context_ratio": len(browser_steps) / len(workflow.steps) if workflow.steps else 0,
        }

    def _get_tool_details(self, tool_names: List[str]) -> List[Dict[str, str]]:
        """Get detailed information about tools"""
        # This would ideally use the tool loader to get tool descriptions
        # For now, return basic info
        return [{"name": name, "description": f"Tool: {name}"} for name in tool_names]
