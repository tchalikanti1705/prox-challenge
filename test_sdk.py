# test_sdk.py — delete this file after testing
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

async def main():
    async for message in query(
        prompt="Say hello in one sentence.",
        options=ClaudeAgentOptions(
            allowed_tools=[],
            permission_mode="bypassPermissions",
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)

asyncio.run(main())