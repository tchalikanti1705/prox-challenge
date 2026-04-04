"""
Tool: search_manual_images
Find and retrieve images from the manual.

Used when user asks about visual content - wiring diagrams, front panel,
wire feed mechanism, weld examples. Also when showing relevant visuals.
"""
import json
from knowledge.store import store

TOOL_DEFINITION = {
    "name": "search_manual_images",
    "description": (
        "Search for relevant images/diagrams from the manual. "
        "Use when the answer would benefit from showing a visual from the manual. "
        "Returns image metadata including descriptions and file references."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What the image should show (e.g. 'wiring diagram', 'front panel controls')"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Filter tags: wiring, diagram, polarity, front_panel, "
                    "wire_feed, weld_diagnosis, troubleshooting, parts, safety"
                )
            }
        },
        "required": ["query"]
    }
}


def execute(params: dict) -> str:
    """Execute search and return JSON string."""
    query = params.get("query", "")
    tags = params.get("tags", [])
    
    results = store.search_images(query=query, tags=tags)
    
    if not results:
        return json.dumps({"message": "No relevant images found"})
    
    return json.dumps({
        "count": len(results),
        "images": results
    }, indent=2)
