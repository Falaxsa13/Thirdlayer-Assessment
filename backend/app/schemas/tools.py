from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class ToolCategory(str, Enum):
    """Categories of tools and integrations"""
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    STORAGE = "storage"
    CRM = "crm"
    ANALYTICS = "analytics"
    DEVELOPMENT = "development"
    OTHER = "other"


class ParameterType(str, Enum):
    """Types of tool parameters"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NUMBER = "number"


class ToolParameter(BaseModel):
    """Definition of a tool parameter"""
    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(..., description="Parameter type")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(False, description="Whether parameter is required")
    default_value: Optional[Any] = Field(None, description="Default value for the parameter")
    enum_values: Optional[List[str]] = Field(None, description="Allowed values for enum parameters")


class ToolSchema(BaseModel):
    """JSON schema for a tool's input parameters"""
    type: str = Field("object", description="Schema type")
    properties: Dict[str, ToolParameter] = Field(..., description="Parameter definitions")
    required: List[str] = Field(default_factory=list, description="Required parameter names")


class ToolDefinition(BaseModel):
    """Definition of an available tool or integration"""
    name: str = Field(..., description="Tool name (e.g., 'google-sheets-add-rows')")
    label: str = Field(..., description="Human-readable tool label")
    description: str = Field(..., description="Tool description")
    category: ToolCategory = Field(ToolCategory.OTHER, description="Tool category")
    input_schema: ToolSchema = Field(..., description="Input parameter schema")
    output_schema: Optional[ToolSchema] = Field(None, description="Output data schema")
    is_active: bool = Field(True, description="Whether tool is currently available")
    rate_limit: Optional[int] = Field(None, description="Rate limit per minute")
    cost_per_call: Optional[float] = Field(None, description="Cost per API call")
    
    @property
    def required_parameters(self) -> List[str]:
        """Get list of required parameter names"""
        return self.input_schema.required
    
    @property
    def optional_parameters(self) -> List[str]:
        """Get list of optional parameter names"""
        all_params = set(self.input_schema.properties.keys())
        required_params = set(self.input_schema.required)
        return list(all_params - required_params)


class ToolExecution(BaseModel):
    """Record of a tool execution"""
    tool_name: str = Field(..., description="Name of the executed tool")
    parameters: Dict[str, Any] = Field(..., description="Parameters used for execution")
    execution_time: float = Field(..., description="Execution time in seconds")
    success: bool = Field(..., description="Whether execution was successful")
    output: Optional[Dict[str, Any]] = Field(None, description="Tool output data")
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    timestamp: int = Field(..., description="Execution timestamp")


class ToolsCatalog(BaseModel):
    """Catalog of available tools and integrations"""
    tools: List[ToolDefinition] = Field(..., description="List of available tools")
    last_updated: int = Field(..., description="Last update timestamp")
    version: str = Field("1.0.0", description="Catalog version")
    
    @property
    def active_tools(self) -> List[ToolDefinition]:
        """Get only active tools"""
        return [tool for tool in self.tools if tool.is_active]
    
    @property
    def tools_by_category(self) -> Dict[ToolCategory, List[ToolDefinition]]:
        """Group tools by category"""
        result = {}
        for tool in self.active_tools:
            if tool.category not in result:
                result[tool.category] = []
            result[tool.category].append(tool)
        return result
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a specific tool by name"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def get_tools_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get tools by category"""
        return [tool for tool in self.active_tools if tool.category == category]
