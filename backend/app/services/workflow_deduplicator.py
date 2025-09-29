from typing import List, Dict, Optional
from loguru import logger
import json
from pathlib import Path

from app.schemas.workflows import WorkflowSchema
from app.services.utils import load_prompt
from openai import OpenAI
from app.core.config import settings


class WorkflowDeduplicator:
    """LLM-powered service for deduplicating similar workflows"""

    def __init__(self, workflows_dir: str = "workflows", similarity_threshold: float = 0.7):
        self.workflows_dir = Path(workflows_dir)
        self.similarity_threshold = similarity_threshold
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def deduplicate_workflows(self, workflows: List[WorkflowSchema]) -> List[WorkflowSchema]:
        """Remove duplicate workflows using LLM analysis against existing workflows"""
        if not workflows:
            return []

        logger.info(f"Starting LLM deduplication of {len(workflows)} workflows against existing workflows")

        # Group by domain and deduplicate each domain
        workflows_by_domain = self._group_by_domain(workflows)
        unique_workflows = []

        for domain, domain_workflows in workflows_by_domain.items():
            logger.info(f"Deduplicating {len(domain_workflows)} workflows for domain: {domain}")

            # Get existing workflows for this domain
            existing_workflows = self._get_existing_workflows_from_json(domain_filter=domain, limit=100)
            logger.info(f"Found {len(existing_workflows)} existing workflows for domain: {domain}")

            # Deduplicate against existing workflows
            if existing_workflows:
                final_unique = await self._deduplicate_against_existing(domain_workflows, existing_workflows)
            else:
                # No existing workflows, just deduplicate within current batch
                final_unique = await self._deduplicate_within_batch(domain_workflows)

            unique_workflows.extend(final_unique)
            logger.info(f"Kept {len(final_unique)} unique workflows for domain: {domain}")

        logger.info(f"LLM deduplication complete: {len(workflows)} → {len(unique_workflows)} workflows")
        return unique_workflows

    def _group_by_domain(self, workflows: List[WorkflowSchema]) -> Dict[str, List[WorkflowSchema]]:
        """Group workflows by domain"""
        grouped = {}
        for workflow in workflows:
            domain = workflow.domain or "unknown"
            if domain not in grouped:
                grouped[domain] = []
            grouped[domain].append(workflow)
        return grouped

    def _get_existing_workflows_from_json(
        self, domain_filter: Optional[str] = None, limit: Optional[int] = None
    ) -> List[Dict]:
        """Get existing workflows from JSON files in compact format for LLM comparison"""
        try:
            if not self.workflows_dir.exists():
                return []

            compact_workflows = []
            json_files = sorted(self.workflows_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)

            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        workflow_data = json.load(f)

                    metadata = workflow_data.get("metadata", {})
                    workflow = workflow_data.get("workflow", {})
                    domain = metadata.get("domain") or workflow.get("domain") or "unknown"

                    # Apply domain filter
                    if domain_filter and domain != domain_filter:
                        continue

                    # Extract tool information
                    steps = workflow.get("steps", [])
                    tool_names = []
                    for step in steps:
                        if step.get("step_type") == "tool" and step.get("tools"):
                            tool_names.extend(step.get("tools", []))

                    compact_workflow = {
                        "id": json_file.stem,
                        "summary": metadata.get("summary") or workflow.get("summary", ""),
                        "domain": domain,
                        "url_pattern": metadata.get("url_pattern") or workflow.get("url_pattern", ""),
                        "step_count": len(steps),
                        "tool_names": list(set(tool_names)),
                    }
                    compact_workflows.append(compact_workflow)

                    if limit and len(compact_workflows) >= limit:
                        break

                except Exception as e:
                    logger.warning(f"Failed to parse workflow file {json_file}: {e}")
                    continue

            return compact_workflows

        except Exception as e:
            logger.error(f"Failed to retrieve existing workflows from JSON: {e}")
            return []

    async def _deduplicate_against_existing(
        self, new_workflows: List[WorkflowSchema], existing_workflows: List[Dict]
    ) -> List[WorkflowSchema]:
        """Deduplicate new workflows against existing ones using LLM"""
        # Prepare data for LLM analysis
        workflow_data = []

        # Add new workflows
        for i, workflow in enumerate(new_workflows):
            workflow_data.append(
                {
                    "index": i,
                    "summary": workflow.summary,
                    "domain": workflow.domain,
                    "url_pattern": workflow.url_pattern,
                    "steps": [
                        {"description": step.description, "step_type": step.step_type, "tools": step.tools or []}
                        for step in workflow.steps
                    ],
                }
            )

        # Add existing workflows
        for existing in existing_workflows:
            workflow_data.append(
                {
                    "index": f"existing_{existing['id']}",
                    "summary": existing["summary"],
                    "domain": existing["domain"],
                    "url_pattern": existing["url_pattern"],
                    "steps": [
                        {"description": f"Step {i+1}", "step_type": "browser_context", "tools": []}
                        for i in range(existing.get("step_count", 1))
                    ],
                }
            )

        # Use LLM to identify duplicates
        result = await self._analyze_with_llm(workflow_data)

        # Extract unique indices for new workflows only
        groups = result.get("groups", [])
        grouped_new_indices = set()

        for group in groups:
            new_indices = [idx for idx in group if isinstance(idx, int) and idx < len(new_workflows)]
            grouped_new_indices.update(new_indices)

        # Keep only new workflows that are NOT grouped (i.e., unique)
        unique_indices = [i for i in range(len(new_workflows)) if i not in grouped_new_indices]
        return [new_workflows[i] for i in unique_indices]

    async def _deduplicate_within_batch(self, workflows: List[WorkflowSchema]) -> List[WorkflowSchema]:
        """Deduplicate workflows within the current batch using LLM"""
        if len(workflows) <= 1:
            return workflows

        # Prepare workflow data for LLM
        workflow_data = []
        for i, workflow in enumerate(workflows):
            workflow_data.append(
                {
                    "index": i,
                    "summary": workflow.summary,
                    "domain": workflow.domain,
                    "url_pattern": workflow.url_pattern,
                    "steps": [
                        {"description": step.description, "step_type": step.step_type, "tools": step.tools or []}
                        for step in workflow.steps
                    ],
                }
            )

        # Use LLM to analyze similarities
        result = await self._analyze_with_llm(workflow_data)

        # Keep the first workflow from each group
        groups = result.get("groups", [])
        unique_workflows = []

        for group in groups:
            if group and group[0] < len(workflows):
                unique_workflows.append(workflows[group[0]])
                if len(group) > 1:
                    logger.debug(f"Grouped {len(group)} similar workflows, kept: {workflows[group[0]].summary[:50]}...")

        return unique_workflows

    async def _analyze_with_llm(self, workflow_data: List[Dict]) -> Dict:
        """Use LLM to analyze workflow similarities"""
        prompt = load_prompt(
            "workflow_deduplication.txt",
            variables={
                "workflows": json.dumps(workflow_data, indent=2),
                "similarity_threshold": self.similarity_threshold,
            },
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing workflow similarities and identifying duplicates.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            if not response.choices[0].message.content:
                raise Exception("No response from LLM")

            result_text = response.choices[0].message.content.strip()
            logger.debug(f"LLM deduplication response: {result_text}")

            # Parse JSON response (handle markdown code blocks)
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            return json.loads(result_text.strip())

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            # Fallback: treat all as unique
            return {"groups": [[i] for i in range(len(workflow_data))]}
