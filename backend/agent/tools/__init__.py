"""
Tool registry - all tools registered here.

To add a new tool:
1. Create a file in agent/tools/
2. Import it here
3. Add to TOOL_DEFINITIONS and TOOL_EXECUTORS

Includes LRU caching for tool results — same input = same output.
"""
import json
from functools import lru_cache

from agent.tools import (
    search_tool,
    duty_cycle_tool,
    polarity_tool,
    troubleshoot_tool,
    image_tool,
    specs_tool,
)
from config import TOOL_CACHE_SIZE

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


@lru_cache(maxsize=TOOL_CACHE_SIZE)
def _execute_cached(name: str, params_json: str) -> str:
    """Cache tool results by (name, params) — same input always returns same output."""
    executor = TOOL_EXECUTORS.get(name)
    if not executor:
        return f"Unknown tool: {name}"
    params = json.loads(params_json)
    return executor(params)


def execute_tool(name: str, params: dict) -> str:
    """Execute a tool by name with caching. Returns result string."""
    try:
        # Serialize params for hashable cache key
        params_json = json.dumps(params, sort_keys=True)
        return _execute_cached(name, params_json)
    except Exception as e:
        return f"Error executing {name}: {str(e)}"
