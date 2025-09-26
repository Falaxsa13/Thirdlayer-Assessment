from typing import Dict, Any
from loguru import logger
from pathlib import Path


def load_prompt(prompt_file: str, variables: Dict[str, Any] = {}) -> str:
    """Load a prompt from file and substitute variables"""
    prompt_path = Path("prompts") / prompt_file

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    if variables:
        try:
            return prompt_template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")

    return prompt_template
