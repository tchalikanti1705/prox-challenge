"""
Tool: search_knowledge
Search the Vulcan OmniPro 220 manual for general information.

Used for open-ended questions about setup, operation, maintenance, etc.
"""
from knowledge.store import store

TOOL_DEFINITION = {
    "name": "search_knowledge",
    "description": (
        "Search the Vulcan OmniPro 220 manual for information. "
        "Use this for general questions about setup, operation, maintenance, "
        "safety, or any topic not covered by the specific lookup tools. "
        "Returns the most relevant sections from the manual."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for in the manual"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}


def execute(params: dict) -> str:
    """Execute search and return formatted results."""
    query = params.get("query", "")
    top_k = params.get("top_k", 5)
    
    results = store.search(query, top_k)
    
    if not results:
        return "No relevant information found in the manual."
    
    # Format as readable text for Claude
    output = []
    for i, result in enumerate(results, 1):
        relevance = result.get("score", 0)
        page = result.get("page", "?")
        section = result.get("section", "Unknown")
        text = result.get("text", "")
        
        entry = (
            f"[Result {i} | Page {page} | Section: {section} | Relevance: {relevance:.2f}]\n"
            f"{text[:500]}...\n"
            "---"
        )
        output.append(entry)
    
    return "\n".join(output)
