"""A thin LLM interface so the agent can be tested with a scripted fake and no API key."""
import os
from typing import Any, Protocol

Message = dict[str, Any]


class LLM(Protocol):
    def create(self, system: str, messages: list[Message], tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return the assistant's content blocks: {"type": "text"|"tool_use", ...}."""
        ...


class AnthropicLLM:
    """Real implementation. The API key is read from the environment only, never from code or files."""

    def __init__(self, model: str | None = None) -> None:
        import anthropic

        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Set the ANTHROPIC_API_KEY environment variable (see .env.example)")
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model or os.environ.get("AGENT_MODEL", "claude-sonnet-5-5")

    def create(self, system: str, messages: list[Message], tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=system,
            messages=messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
        )
        blocks: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                blocks.append({"type": "tool_use", "id": block.id, "name": block.name, "input": dict(block.input)})
        return blocks
