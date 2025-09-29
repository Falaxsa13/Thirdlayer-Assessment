from typing import List, Dict, Optional, Any
from loguru import logger
import json
import os
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
        """Remove duplicate workflows using efficient batch LLM analysis against existing workflows

        Args:
            workflows: New workflows to deduplicate
            max_existing_per_domain: Maximum existing workflows to compare against per domain (for efficiency)
        """
        if not workflows:
            return []

        logger.info(f"Starting efficient LLM deduplication of {len(workflows)} workflows against existing workflows")

        # First deduplicate within current batch
        workflows_by_domain = self._group_by_domain(workflows)
        unique_workflows = []

        for domain, domain_workflows in workflows_by_domain.items():
            logger.info(f"Deduplicating {len(domain_workflows)} workflows for domain: {domain}")

            # Deduplicate within current batch first
            domain_unique = await self._deduplicate_within_domain_llm(domain_workflows)

            existing_workflows = self._get_existing_workflows_from_json(domain_filter=domain, limit=100)

            logger.info(
                f"Found {len([w for w in existing_workflows if w.get('domain') == domain])} existing workflows for domain: {domain}"
            )

            # Then efficiently deduplicate against existing workflows using batch comparison
            final_unique = await self._efficient_batch_deduplication(domain_unique, existing_workflows, domain)
            unique_workflows.extend(final_unique)

            logger.info(f"Kept {len(final_unique)} unique workflows for domain: {domain}")

        logger.info(f"Efficient LLM deduplication complete: {len(workflows)} → {len(unique_workflows)} workflows")
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
        """Get existing workflows from JSON files in compact format for LLM comparison

        Args:
            domain_filter: Optional domain to filter workflows (for efficiency)
            limit: Optional limit for CRON job scenarios with many existing workflows
        """
        try:
            if not self.workflows_dir.exists():
                logger.debug(f"Workflows directory does not exist: {self.workflows_dir}")
                return []

            compact_workflows = []

            # Get all JSON files sorted by modification time (newest first)
            json_files = sorted(self.workflows_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)

            for json_file in json_files:
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        workflow_data = json.load(f)

                    # Extract workflow info from JSON structure
                    metadata = workflow_data.get("metadata", {})
                    workflow = workflow_data.get("workflow", {})

                    domain = metadata.get("domain") or workflow.get("domain") or "unknown"

                    # Apply domain filter if provided
                    if domain_filter and domain != domain_filter:
                        continue

                    # Extract step information
                    steps = workflow.get("steps", [])
                    step_types = [step.get("step_type", "browser_context") for step in steps]

                    # Extract tool information
                    tool_names = []
                    has_tools = False
                    for step in steps:
                        if step.get("step_type") == "tool" and step.get("tools"):
                            tool_names.extend(step.get("tools", []))
                            has_tools = True

                    compact_workflow = {
                        "id": json_file.stem,  # Use filename as ID
                        "summary": metadata.get("summary") or workflow.get("summary", ""),
                        "domain": domain,
                        "url_pattern": metadata.get("url_pattern") or workflow.get("url_pattern", ""),
                        "step_count": metadata.get("step_count", len(steps)),
                        "has_tools": metadata.get("has_tools", has_tools),
                        "step_types": step_types,
                        "tool_names": list(set(tool_names)),
                        "created_at": metadata.get("created_at", ""),
                    }
                    compact_workflows.append(compact_workflow)

                    # Apply limit if provided
                    if limit and len(compact_workflows) >= limit:
                        break

                except Exception as e:
                    logger.warning(f"Failed to parse workflow file {json_file}: {e}")
                    continue

            logger.debug(f"Retrieved {len(compact_workflows)} existing workflows from JSON files")
            return compact_workflows

        except Exception as e:
            logger.error(f"Failed to retrieve existing workflows from JSON: {e}")
            return []

    async def _efficient_batch_deduplication(
        self, new_workflows: List[WorkflowSchema], existing_workflows: List[Dict], domain: str
    ) -> List[WorkflowSchema]:
        """Efficiently deduplicate new workflows against existing ones using progressive batch comparison"""
        if not new_workflows or not existing_workflows:
            return new_workflows

        # Filter existing workflows by domain for efficiency
        domain_existing = [w for w in existing_workflows if w.get("domain") == domain]
        if not domain_existing:
            logger.debug(f"No existing workflows found for domain: {domain}")
            return new_workflows

        logger.info(
            f"Efficiently comparing {len(new_workflows)} new workflows against {len(domain_existing)} existing workflows for domain: {domain}"
        )

        # Progressive batch comparison: compare batches of new workflows against batches of existing workflows
        remaining_workflows = new_workflows.copy()
        unique_workflows = []
        batch_size = 10  # Compare 10 new workflows at a time
        existing_batch_size = 25  # Against 25 existing workflows at a time

        while remaining_workflows:
            # Take a batch of new workflows
            current_batch = remaining_workflows[:batch_size]
            remaining_workflows = remaining_workflows[batch_size:]

            logger.debug(f"Processing batch of {len(current_batch)} new workflows")

            # Compare against batches of existing workflows
            batch_unique = await self._compare_batch_against_existing(
                current_batch, domain_existing, existing_batch_size
            )
            unique_workflows.extend(batch_unique)

            logger.debug(f"Batch completed: {len(current_batch)} → {len(batch_unique)} unique workflows")

        duplicates_found = len(new_workflows) - len(unique_workflows)
        if duplicates_found > 0:
            logger.info(f"Found {duplicates_found} duplicates against existing workflows")

        return unique_workflows

    async def _compare_batch_against_existing(
        self, new_batch: List[WorkflowSchema], existing_workflows: List[Dict], existing_batch_size: int
    ) -> List[WorkflowSchema]:
        """Compare a batch of new workflows against batches of existing workflows"""

        remaining_new = new_batch.copy()
        unique_workflows = []

        # Compare against batches of existing workflows
        for i in range(0, len(existing_workflows), existing_batch_size):
            existing_batch = existing_workflows[i : i + existing_batch_size]

            if not remaining_new:
                break

            logger.debug(
                f"Comparing {len(remaining_new)} new workflows against batch of {len(existing_batch)} existing workflows"
            )

            # Use the existing deduplication logic but with compact data
            batch_result = await self._analyze_batch_deduplication(remaining_new, existing_batch)

            # Filter out duplicates found in this batch
            remaining_new = [remaining_new[j] for j in batch_result.get("unique_indices", [])]

        unique_workflows.extend(remaining_new)
        return unique_workflows

    async def _analyze_batch_deduplication(
        self, new_workflows: List[WorkflowSchema], existing_batch: List[Dict]
    ) -> Dict:
        """Use LLM to analyze batch deduplication using the existing deduplication prompt"""

        # Prepare compact data for LLM (same format as existing deduplication)
        workflow_data = []
        for i, workflow in enumerate(new_workflows):
            workflow_info = {
                "index": i,
                "summary": workflow.summary,
                "domain": workflow.domain,
                "url_pattern": workflow.url_pattern,
                "steps": [
                    {
                        "description": step.description,
                        "step_type": step.step_type,
                        "tools": step.tools or [],
                        "context_description": step.context_description,
                    }
                    for step in workflow.steps
                ],
            }
            workflow_data.append(workflow_info)

        # Add existing workflows to the comparison (treat them as "workflows to analyze")
        for existing in existing_batch:
            workflow_info = {
                "index": f"existing_{existing['id']}",
                "summary": existing["summary"],
                "domain": existing["domain"],
                "url_pattern": existing["url_pattern"],
                "steps": [
                    {
                        "description": f"Step {i+1}",
                        "step_type": step_type,
                        "tools": [],
                        "context_description": f"Step {i+1}",
                    }
                    for i, step_type in enumerate(existing.get("step_types", []))
                ],
            }
            workflow_data.append(workflow_info)

        # Use existing deduplication prompt
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
                raise Exception("No response from LLM for batch deduplication")

            result_text = response.choices[0].message.content.strip()

            logger.debug(f"LLM batch deduplication response: {result_text}")

            # Parse LLM response (handle markdown code blocks)
            try:
                # Remove markdown code blocks if present
                if result_text.startswith("```json"):
                    result_text = result_text[7:]  # Remove ```json
                if result_text.endswith("```"):
                    result_text = result_text[:-3]  # Remove ```
                result_text = result_text.strip()

                result = json.loads(result_text)

                # Extract unique indices for new workflows only (not existing ones)
                groups = result.get("groups", [])
                grouped_new_indices = set()

                # Collect all new workflow indices that are grouped (i.e., duplicates)
                for group in groups:
                    new_indices = [idx for idx in group if isinstance(idx, int) and idx < len(new_workflows)]
                    grouped_new_indices.update(new_indices)

                # Keep only new workflows that are NOT grouped (i.e., unique)
                unique_indices = [i for i in range(len(new_workflows)) if i not in grouped_new_indices]

                logger.debug(
                    f"Batch deduplication completed: {len(new_workflows)} → {len(unique_indices)} unique workflows"
                )
                return {"unique_indices": unique_indices}

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM batch deduplication response as JSON: {e}")
                logger.error(f"LLM response: {result_text}")
                return {"unique_indices": list(range(len(new_workflows)))}  # Fallback: keep all

        except Exception as e:
            logger.error(f"LLM batch deduplication analysis failed: {e}")
            return {"unique_indices": list(range(len(new_workflows)))}  # Fallback: keep all

    async def _deduplicate_within_domain_llm(self, workflows: List[WorkflowSchema]) -> List[WorkflowSchema]:
        """Deduplicate workflows within the same domain using LLM analysis"""
        if len(workflows) <= 1:
            return workflows

        # Prepare workflow data for LLM analysis
        workflow_data = []
        for i, workflow in enumerate(workflows):
            workflow_info = {
                "index": i,
                "summary": workflow.summary,
                "domain": workflow.domain,
                "url_pattern": workflow.url_pattern,
                "steps": [
                    {
                        "description": step.description,
                        "step_type": step.step_type,
                        "tools": step.tools or [],
                        "context_description": step.context_description,
                    }
                    for step in workflow.steps
                ],
            }
            workflow_data.append(workflow_info)

        # Use LLM to analyze similarities and group workflows
        similarity_analysis = await self._analyze_workflow_similarities(workflow_data)

        # Process LLM results to get unique workflows
        unique_workflows = self._process_similarity_analysis(workflows, similarity_analysis)

        return unique_workflows

    async def _analyze_workflow_similarities(self, workflow_data: List[Dict]) -> Dict:
        """Use LLM to analyze workflow similarities and group them"""

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
                raise Exception("No response from LLM for workflow deduplication")

            result_text = response.choices[0].message.content.strip()

            logger.debug(f"LLM similarity analysis response: {result_text}")

            # Parse LLM response (handle markdown code blocks)
            try:
                # Remove markdown code blocks if present
                if result_text.startswith("```json"):
                    result_text = result_text[7:]  # Remove ```json
                if result_text.endswith("```"):
                    result_text = result_text[:-3]  # Remove ```
                result_text = result_text.strip()

                result = json.loads(result_text)
                logger.debug(f"LLM similarity analysis completed: {len(result.get('groups', []))} groups identified")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"LLM response: {result_text}")
                return {"groups": [[i] for i in range(len(workflow_data))]}  # Fallback: treat all as unique

        except Exception as e:
            logger.error(f"LLM similarity analysis failed: {e}")
            return {"groups": [[i] for i in range(len(workflow_data))]}  # Fallback: treat all as unique

    def _process_similarity_analysis(self, workflows: List[WorkflowSchema], analysis: Dict) -> List[WorkflowSchema]:
        """Process LLM similarity analysis to select unique workflows"""
        groups = analysis.get("groups", [])
        unique_workflows = []

        for group in groups:
            if not group:
                continue

            # Get workflows in this group
            group_workflows = [workflows[i] for i in group if i < len(workflows)]

            if not group_workflows:
                continue

            # Select the best workflow from the group
            if len(group_workflows) == 1:
                best_workflow = group_workflows[0]
            else:
                best_workflow = self._select_best_workflow_from_group(group_workflows)

            unique_workflows.append(best_workflow)

            if len(group_workflows) > 1:
                logger.debug(f"Grouped {len(group_workflows)} similar workflows, kept: {best_workflow.summary[:50]}...")

        return unique_workflows

    def _select_best_workflow_from_group(self, workflows: List[WorkflowSchema]) -> WorkflowSchema:
        """Select the best workflow from a group of similar workflows"""
        if len(workflows) == 1:
            return workflows[0]

        # Scoring criteria (higher is better)
        best_workflow = workflows[0]
        best_score = self._calculate_workflow_quality_score(best_workflow)

        for workflow in workflows[1:]:
            score = self._calculate_workflow_quality_score(workflow)
            if score > best_score:
                best_score = score
                best_workflow = workflow

        return best_workflow

    def _calculate_workflow_quality_score(self, workflow: WorkflowSchema) -> float:
        """Calculate a quality score for workflow selection"""
        score = 0.0

        # Prefer workflows with more steps (more complete)
        score += len(workflow.steps) * 0.1

        # Prefer workflows with tools (more actionable)
        tool_count = sum(len(step.tools or []) for step in workflow.steps)
        score += tool_count * 0.2

        # Prefer workflows with longer, more descriptive summaries
        score += len(workflow.summary) * 0.01

        # Prefer workflows with specific URL patterns
        if workflow.url_pattern and "*" not in workflow.url_pattern:
            score += 0.5

        return score
