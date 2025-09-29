from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Definition of an available tool or integration"""

    name: str = Field(..., description="Tool name (e.g., 'slack-send-message')")
    label: str = Field(..., description="Human-readable tool label")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for input parameters")

    @property
    def required_parameters(self) -> List[str]:
        """Get list of required parameter names"""
        return self.input_schema.get("jsonSchema", {}).get("required", [])

    @property
    def optional_parameters(self) -> List[str]:
        """Get list of optional parameter names"""
        schema = self.input_schema.get("jsonSchema", {})
        all_params = set(schema.get("properties", {}).keys())
        required_params = set(schema.get("required", []))
        return list(all_params - required_params)

    def get_parameter_description(self, param_name: str) -> str:
        """Get description for a specific parameter"""
        schema = self.input_schema.get("jsonSchema", {})
        param_def = schema.get("properties", {}).get(param_name, {})
        return param_def.get("description", "")


class ToolsCatalog(BaseModel):
    """Catalog of available tools and integrations"""

    tools: List[ToolDefinition] = Field(..., description="List of available tools")

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a specific tool by name"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def get_tool_names(self) -> List[str]:
        """Get list of all tool names"""
        return [tool.name for tool in self.tools]
