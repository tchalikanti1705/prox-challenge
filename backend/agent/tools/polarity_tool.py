"""
Tool: lookup_polarity
Look up polarity and socket connections for each process.

Used for polarity, wiring, terminal, socket, cable connection questions.
"""
import json
from knowledge.store import store

TOOL_DEFINITION = {
    "name": "lookup_polarity",
    "description": (
        "Look up the correct polarity and socket connections for a welding process. "
        "Returns which terminal the torch/electrode connects to and which terminal "
        "the ground clamp connects to."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "process": {
                "type": "string",
                "description": "Welding process: MIG, Flux-Cored, TIG, or Stick"
            }
        },
        "required": ["process"]
    }
}


def execute(params: dict) -> str:
    """Execute lookup and return JSON string."""
    process = params.get("process", "").strip()
    
    result = store.get_polarity(process)
    
    return json.dumps(result, indent=2)
