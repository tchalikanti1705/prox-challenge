"""
Tool: get_specifications
Look up general specifications of the Vulcan OmniPro 220.

Used for questions about voltage, amperage range, wire sizes, weight,
processes supported, dimensions, etc.
"""
import json
from knowledge.store import store

TOOL_DEFINITION = {
    "name": "get_specifications",
    "description": (
        "Get the technical specifications of the Vulcan OmniPro 220. "
        "Returns all specs: voltage, amperage, processes, wire sizes, etc."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


def execute(params: dict) -> str:
    """Execute lookup and return JSON string."""
    specs = store.get_specs()
    
    return json.dumps(specs, indent=2)
