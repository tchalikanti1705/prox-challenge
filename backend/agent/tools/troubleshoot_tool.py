"""
Tool: get_troubleshooting
Get troubleshooting guidance for welding problems.

Used when user reports a problem: porosity, spatter, wire feed issues, arc issues, etc.
"""
import json
from knowledge.store import store

TOOL_DEFINITION = {
    "name": "get_troubleshooting",
    "description": (
        "Get troubleshooting guidance for a welding problem. "
        "Returns possible causes and step-by-step fixes from the manual."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symptom": {
                "type": "string",
                "description": (
                    "The problem: porosity, spatter, wire feed issues, no arc, "
                    "unstable arc, undercut, burn-through, etc."
                )
            }
        },
        "required": ["symptom"]
    }
}


def execute(params: dict) -> str:
    """Execute lookup and return JSON string."""
    symptom = params.get("symptom", "").strip()
    
    result = store.get_troubleshooting(symptom)
    
    return json.dumps(result, indent=2)
