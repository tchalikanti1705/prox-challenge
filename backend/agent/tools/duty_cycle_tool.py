"""
Tool: lookup_duty_cycle
Exact duty cycle lookup from the manual.

Used for any question about duty cycle, weld time, cooling, amperage limits.
Never guess - always use this tool first for duty cycle questions.
"""
import json
from knowledge.store import store

TOOL_DEFINITION = {
    "name": "lookup_duty_cycle",
    "description": (
        "Look up the exact duty cycle for a specific welding process, "
        "voltage, and amperage from the manual. "
        "ALWAYS use this tool for duty cycle questions — never guess. "
        "Returns the precise percentage and all related ratings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "process": {
                "type": "string",
                "description": "Welding process: MIG, Flux-Cored, TIG, or Stick",
                "enum": ["MIG", "Flux-Cored", "TIG", "Stick"]
            },
            "voltage": {
                "type": "string",
                "description": "Input voltage: 120V or 240V",
                "enum": ["120V", "240V"]
            },
            "amperage": {
                "type": "string",
                "description": "Amperage to look up (e.g. '200A'). Optional — omit to get all ratings."
            }
        },
        "required": ["process", "voltage"]
    }
}


def execute(params: dict) -> str:
    """Execute exact lookup and return JSON string."""
    process = params.get("process", "")
    voltage = params.get("voltage", "")
    amperage = params.get("amperage")
    
    result = store.get_duty_cycle(process, voltage, amperage)
    
    return json.dumps(result, indent=2)
