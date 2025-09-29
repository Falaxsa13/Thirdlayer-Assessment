import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.schemas.tools import ToolDefinition, ToolsCatalog
from loguru import logger


class ToolLoader:
    """Service for loading tools from the tools-dump directory"""

    def __init__(self, tools_dump_path: str = "tools-dump"):
        self.tools_dump_path = Path(tools_dump_path)
        self._tools_cache: Optional[ToolsCatalog] = None

    def load_all_tools(self) -> ToolsCatalog:
        """Load all tools from the tools-dump directory"""
        if self._tools_cache is not None:
            return self._tools_cache

        logger.info("Loading tools from tools-dump directory")
        all_tools = []

        # Get all .txt files in tools-dump directory
        tool_files = list(self.tools_dump_path.glob("*.txt"))
        logger.info(f"Found {len(tool_files)} tool files")

        for tool_file in tool_files:
            try:
                tools_from_file = self._load_tools_from_file(tool_file)
                all_tools.extend(tools_from_file)
                logger.debug(f"Loaded {len(tools_from_file)} tools from {tool_file.name}")
            except Exception as e:
                logger.error(f"Failed to load tools from {tool_file.name}: {str(e)}")

        logger.info(f"Successfully loaded {len(all_tools)} tools total")

        # Create tools catalog
        self._tools_cache = ToolsCatalog(tools=all_tools)

        return self._tools_cache

    def load_tools_by_categories(self, categories: List[str]) -> ToolsCatalog:
        """Load tools only from specified categories"""
        if not categories:
            logger.debug("No categories specified, returning empty catalog")
            return ToolsCatalog(tools=[])

        logger.info(f"Loading tools from categories: {categories}")
        all_tools = []

        for category in categories:
            tool_file = self.tools_dump_path / f"{category}.txt"
            if tool_file.exists():
                try:
                    tools_from_file = self._load_tools_from_file(tool_file)
                    all_tools.extend(tools_from_file)
                    logger.debug(f"Loaded {len(tools_from_file)} tools from {category}")
                except Exception as e:
                    logger.error(f"Failed to load tools from {category}: {str(e)}")
            else:
                logger.warning(f"Tool category file not found: {tool_file}")

        logger.info(f"Successfully loaded {len(all_tools)} tools from {len(categories)} categories")
        return ToolsCatalog(tools=all_tools)

    def _load_tools_from_file(self, file_path: Path) -> List[ToolDefinition]:
        """Load tools from a single file"""
        tools = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        tool_data = json.loads(line)
                        tool_definition = self._parse_tool_definition(tool_data, file_path.name)
                        if tool_definition:
                            tools.append(tool_definition)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in {file_path.name} line {line_num}: {str(e)}")
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to parse tool in {file_path.name} line {line_num}: {str(e)}")
                        continue

        except FileNotFoundError:
            logger.error(f"Tool file not found: {file_path}")
        except Exception as e:
            logger.error(f"Error reading tool file {file_path}: {str(e)}")

        return tools

    def _parse_tool_definition(self, tool_data: Dict[str, Any], source_file: str) -> Optional[ToolDefinition]:
        """Parse a single tool definition from JSON data"""
        try:
            # Extract basic tool information
            name = tool_data.get("name", "")
            label = tool_data.get("label", name)
            description = tool_data.get("description", "")

            if not name:
                logger.warning(f"Tool missing name in {source_file}")
                return None

            # Use input schema directly from tool data
            input_schema = tool_data.get("inputSchema", {})

            return ToolDefinition(
                name=name,
                label=label,
                description=description,
                input_schema=input_schema,
            )

        except Exception as e:
            logger.error(f"Failed to parse tool definition: {str(e)}")
            return None

    def get_tool_by_name(self, name: str) -> Optional[ToolDefinition]:
        """Get a specific tool by name"""
        catalog = self.load_all_tools()
        return catalog.get_tool(name)

    def refresh_cache(self):
        """Clear the tools cache to force reload"""
        self._tools_cache = None
        logger.info("Tools cache cleared")

    def get_available_tool_categories(self) -> List[str]:
        """Get list of available tool categories from tools-dump directory"""
        tool_files = list(self.tools_dump_path.glob("*.txt"))
        return [file.stem for file in tool_files]
