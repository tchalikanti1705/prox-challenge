"""
Agent client — agentic tool-use loop powered by the Anthropic Python SDK.

Implements the full agent loop with streaming:
1. Send user message + tool definitions to Claude
2. Stream text tokens as they arrive for fast display
3. If Claude returns tool_use blocks, execute them in parallel
4. Feed tool results back and let Claude continue reasoning
5. Repeat until Claude produces a final text response (max 10 turns)

Improvements over v1:
- Parallel tool execution via asyncio.gather
- Connection pooling with timeout and retry
- Conversation context trimming (keeps last N messages)
- Tool-specific loading states with emoji labels
"""
import asyncio
import json
from typing import AsyncGenerator, List, Optional, Tuple

from anthropic import AsyncAnthropic

from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOL_DEFINITIONS, execute_tool
from config import ANTHROPIC_API_KEY, MODEL, MAX_TOKENS, MAX_CONVERSATION_MESSAGES


# Connection pooling: single client with timeout and retry
_client = AsyncAnthropic(
    api_key=ANTHROPIC_API_KEY,
    timeout=60.0,
    max_retries=2,
)

MAX_TOOL_TURNS = 10

# Friendly labels for tool names (with emoji for UX)
_TOOL_LABELS = {
    "search_knowledge": "📖 Searching the manual",
    "lookup_duty_cycle": "📊 Looking up duty cycle data",
    "lookup_polarity": "🔌 Checking polarity settings",
    "get_troubleshooting": "🔧 Finding troubleshooting steps",
    "search_manual_images": "🖼️ Searching for diagrams",
    "get_specifications": "📋 Pulling up specifications",
}


def _trim_history(messages: List[dict]) -> List[dict]:
    """
    Trim conversation history to prevent context window overflow.
    
    Keeps the last MAX_CONVERSATION_MESSAGES messages.
    If trimmed, prepends a summary note so Claude has context.
    """
    if len(messages) <= MAX_CONVERSATION_MESSAGES:
        return messages

    trimmed_count = len(messages) - MAX_CONVERSATION_MESSAGES
    recent = messages[-MAX_CONVERSATION_MESSAGES:]

    # Inject a context note as the first message
    summary = {
        "role": "user",
        "content": (
            f"[System note: {trimmed_count} earlier messages were trimmed for context. "
            "The conversation continues below with recent messages.]"
        )
    }
    return [summary] + recent


def _build_messages(
    history: List[dict],
    user_message: str,
    images: Optional[List[str]] = None,
) -> List[dict]:
    """Build the messages array for the Anthropic API."""
    msgs: List[dict] = []

    # Trim history before building
    trimmed_history = _trim_history(history)

    for msg in trimmed_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            msgs.append({"role": role, "content": content})

    if images:
        content_blocks = []
        for img_b64 in images:
            # Auto-detect media type from base64 magic bytes
            if img_b64.startswith("iVBOR"):
                media_type = "image/png"
            elif img_b64.startswith("/9j/"):
                media_type = "image/jpeg"
            elif img_b64.startswith("UklGR"):
                media_type = "image/webp"
            elif img_b64.startswith("R0lGO"):
                media_type = "image/gif"
            else:
                media_type = "image/png"
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": img_b64,
                },
            })
        content_blocks.append({"type": "text", "text": user_message or "What do you see in these images?"})
        msgs.append({"role": "user", "content": content_blocks})
    else:
        msgs.append({"role": "user", "content": user_message})

    return msgs


async def _execute_tool_async(name: str, params: dict) -> str:
    """Execute a tool in a thread pool (non-blocking for async)."""
    return await asyncio.to_thread(execute_tool, name, params)


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
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield ("text", event.delta.text)
                        text_parts.append(event.delta.text)

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

            final_message = await stream.get_final_message()

        # If no tool calls, we're done
        if not tool_calls:
            break

        # Execute tools IN PARALLEL and continue the loop
        api_messages.append({"role": "assistant", "content": final_message.content})

        # Show tool labels for all tools being called
        tool_names = [_TOOL_LABELS.get(tc["name"], tc["name"]) for tc in tool_calls]
        yield ("thinking", " | ".join(tool_names) + "...")

        # Build parallel tasks
        tasks = []
        for tc in tool_calls:
            tool_input = {}
            for block in final_message.content:
                if hasattr(block, "id") and block.id == tc["id"]:
                    tool_input = block.input
                    break
            tasks.append((tc["id"], tc["name"], tool_input))

        # Execute all tools concurrently
        async_tasks = [_execute_tool_async(name, params) for _, name, params in tasks]
        results = await asyncio.gather(*async_tasks, return_exceptions=True)

        tool_results = []
        for (tc_id, tc_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                result_str = f"Error executing {tc_name}: {str(result)}"
            else:
                result_str = result
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc_id,
                "content": result_str,
            })

        api_messages.append({"role": "user", "content": tool_results})

        if final_message.stop_reason == "end_turn":
            break
