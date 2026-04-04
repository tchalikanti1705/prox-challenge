"""
Tool registry - all tools registered here.

To add a new tool:
1. Create a file in agent/tools/
2. Import it here
3. Add to TOOL_DEFINITIONS and TOOL_EXECUTORS
"""
from agent.tools import (
    search_tool,
    duty_cycle_tool,
    polarity_tool,
    troubleshoot_tool,
    image_tool,
    specs_tool,
)

# Tool definitions sent to Claude (so it knows what tools exist)
TOOL_DEFINITIONS = [
    search_tool.TOOL_DEFINITION,
    duty_cycle_tool.TOOL_DEFINITION,
    polarity_tool.TOOL_DEFINITION,
    troubleshoot_tool.TOOL_DEFINITION,
    image_tool.TOOL_DEFINITION,
    specs_tool.TOOL_DEFINITION,
]

# Tool executors (called when Claude wants to use a tool)
TOOL_EXECUTORS = {
    "search_knowledge": search_tool.execute,
    "lookup_duty_cycle": duty_cycle_tool.execute,
    "lookup_polarity": polarity_tool.execute,
    "get_troubleshooting": troubleshoot_tool.execute,
    "search_manual_images": image_tool.execute,
    "get_specifications": specs_tool.execute,
}


def execute_tool(name: str, params: dict) -> str:
    """Execute a tool by name. Returns result string."""
    executor = TOOL_EXECUTORS.get(name)
    if not executor:
        return f"Unknown tool: {name}"
    try:
        return executor(params)
    except Exception as e:
        return f"Error executing {name}: {str(e)}"
