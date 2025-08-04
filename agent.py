from __future__ import annotations

import json
from typing import Any, List

from fastmcp import Client
from langfuse import Langfuse, observe
from mcp.types import Tool as MCPTool
from openai import AsyncOpenAI
from openai.types import chat

from settings import Settings


class Agent:
    """Agent handling chat completions and MCP tool calls."""

    def __init__(self, settings: Settings) -> None:
        self.settings: Settings = settings
        self.client: AsyncOpenAI = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.langfuse: Langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        self.mcp_client: Client = Client(settings.mcp_config)

    def _mcp_tool_to_openai(self, tool: MCPTool) -> chat.ChatCompletionToolParam:
        return chat.ChatCompletionToolParam(
            type="function",
            function={
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema
                or {"type": "object", "properties": {}},
            },
        )

    @observe()
    async def run(
        self,
        messages: List[chat.ChatCompletionMessageParam],
        model: str | None = None,
    ) -> chat.ChatCompletion:
        """Generate a chat completion handling any MCP tool calls."""

        conversation: List[chat.ChatCompletionMessageParam] = list(messages)
        tools: List[chat.ChatCompletionToolParam] = []

        try:
            async with self.mcp_client as mcp:
                try:
                    mcp_tools = await mcp.list_tools()
                    tools = [self._mcp_tool_to_openai(t) for t in mcp_tools]
                except Exception:
                    tools = []

                while True:
                    response = await self._generate(conversation, tools, model)
                    message = response.choices[0].message
                    conversation.append(message.model_dump())

                    tool_calls = getattr(message, "tool_calls", None)
                    if not tool_calls:
                        break

                    for call in tool_calls:
                        args = json.loads(call.function.arguments or "{}")
                        try:
                            result = await mcp.call_tool(call.function.name, args)
                            content = (
                                result.data
                                if result.data is not None
                                else result.structured_content or result.content
                            )
                        except Exception as exc:  # pragma: no cover - best effort
                            content = {"error": str(exc)}

                        conversation.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": json.dumps(content),
                            }
                        )
        except Exception:  # pragma: no cover - best effort fallback
            response = await self._generate(conversation, [], model)

        self.langfuse.flush()

        return response

    @observe(as_type="generation")
    async def _generate(
        self,
        conversation: List[chat.ChatCompletionMessageParam],
        tools: List[chat.ChatCompletionToolParam],
        model: str | None,
    ) -> chat.ChatCompletion:
        kwargs: dict[str, Any] = {}
        if tools:
            kwargs["tools"] = tools
        return await self.client.chat.completions.create(
            model=model or self.settings.openai_model,
            messages=conversation,
            **kwargs,
        )
