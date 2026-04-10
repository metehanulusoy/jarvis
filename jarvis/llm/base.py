"""LLM backend protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass
class Message:
    role: str  # "system", "user", "assistant"
    content: str


class LLMBackend(Protocol):
    def chat(self, messages: list[Message], temperature: float = 0.7) -> str: ...
    def stream(self, messages: list[Message], temperature: float = 0.7) -> Iterator[str]: ...
    def is_available(self) -> bool: ...
    @property
    def name(self) -> str: ...
