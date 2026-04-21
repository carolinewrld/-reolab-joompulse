"""Anthropic async client + helpers for structured, cache-aware calls."""

from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message

from joompulse.config import get_settings


@lru_cache(maxsize=1)
def get_anthropic() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key.get_secret_value())


@dataclass(slots=True)
class CachedSystem:
    """A system prompt composed of 1..N blocks, with cache marker on the last."""

    static_block: str   # e.g. general system behaviour
    cached_block: str   # e.g. taxonomy — stable, large, cache-worthy

    def to_api(self) -> list[dict[str, Any]]:
        return [
            {"type": "text", "text": self.static_block},
            {
                "type": "text",
                "text": self.cached_block,
                "cache_control": {"type": "ephemeral"},
            },
        ]


def image_block(jpeg: bytes, media_type: str = "image/jpeg") -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(jpeg).decode(),
        },
    }


def text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


async def call_with_tool(
    *,
    model: str,
    system: CachedSystem,
    user_content: Sequence[dict[str, Any]],
    tool: dict[str, Any],
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> tuple[Message, dict[str, Any]]:
    """Issue a Claude call forcing a single tool invocation and return its input."""
    client = get_anthropic()
    message = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system.to_api(),
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": list(user_content)}],
    )

    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == tool["name"]:
            return message, dict(block.input)  # type: ignore[arg-type]

    raise RuntimeError(
        f"Claude did not call tool {tool['name']!r}; stop_reason={message.stop_reason}"
    )
