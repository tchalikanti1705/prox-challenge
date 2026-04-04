"""
Agent client — agentic tool-use loop powered by the Anthropic Python SDK.

Implements the full agent loop with streaming:
1. Send user message + tool definitions to Claude
2. Stream text tokens as they arrive for fast display
3. If Claude returns tool_use blocks, execute them locally
4. Feed tool results back and let Claude continue reasoning
5. Repeat until Claude produces a final text response (max 10 turns)

Yields (event_type, data) tuples so the route can emit typed SSE events.
"""
import json
from typing import AsyncGenerator, List, Optional, Tuple

from anthropic import AsyncAnthropic

from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOL_DEFINITIONS, execute_tool
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS


_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

MAX_TOOL_TURNS = 10

# Friendly labels for tool names
_TOOL_LABELS = {
    "search_knowledge": "Searching the manual",
    "lookup_duty_cycle": "Looking up duty cycle data",
    "lookup_polarity": "Checking polarity settings",
    "get_troubleshooting": "Finding troubleshooting steps",
    "search_manual_images": "Searching for diagrams",
    "get_specifications": "Pulling up specifications",
}


def _build_messages(
    history: List[dict],
    user_message: str,
    images: Optional[List[str]] = None,
) -> List[dict]:
    """Build the messages array for the Anthropic API."""
    msgs: List[dict] = []

    for msg in history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            msgs.append({"role": role, "content": content})

    if images:
        content_blocks = []
        for img_b64 in images:
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64,
                },
            })
        content_blocks.append({"type": "text", "text": user_message or "What do you see in these images?"})
        msgs.append({"role": "user", "content": content_blocks})
    else:
        msgs.append({"role": "user", "content": user_message})

    return msgs


async def chat(
    messages: List[dict],
    user_message: str,
    images: Optional[List[str]] = None,
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Run the agentic tool-use loop with streaming.

    Yields (event_type, data) tuples:
      - ("thinking", message)  — status updates while agent works
      - ("text", chunk)       — streamed text tokens
    """
    api_messages = _build_messages(messages, user_message, images)

    for turn in range(MAX_TOOL_TURNS):
        # Signal that we're thinking
        if turn == 0:
            yield ("thinking", "Thinking...")
        else:
            yield ("thinking", "Analyzing results...")

        # --- Stream the response for fast token delivery ---
        text_parts: list[str] = []
        tool_calls: list[dict] = []
        current_tool: dict = {}

        async with _client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=api_messages,
        ) as stream:
            async for event in stream:
                # Stream text tokens as they arrive
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield ("text", event.delta.text)
                        text_parts.append(event.delta.text)
                    elif hasattr(event.delta, "partial_json"):
                        # Tool input being built — accumulate silently
                        pass

                elif event.type == "content_block_start":
                    if hasattr(event.content_block, "type"):
                        if event.content_block.type == "tool_use":
                            current_tool = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            }

                elif event.type == "content_block_stop":
                    if current_tool:
                        tool_calls.append(current_tool)
                        current_tool = {}

            # Get the final assembled message for history
            final_message = await stream.get_final_message()

        # If no tool calls, we're done
        if not tool_calls:
            break

        # Execute tools and continue the loop
        api_messages.append({"role": "assistant", "content": final_message.content})

        tool_results = []
        for tc in tool_calls:
            label = _TOOL_LABELS.get(tc["name"], tc["name"])
            yield ("thinking", f"{label}...")

            # Find the matching tool_use block to get the parsed input
            tool_input = {}
            for block in final_message.content:
                if hasattr(block, "id") and block.id == tc["id"]:
                    tool_input = block.input
                    break

            result = execute_tool(tc["name"], tool_input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": result,
            })

        api_messages.append({"role": "user", "content": tool_results})

        if final_message.stop_reason == "end_turn":
            break
