"""Ollama local LLM backend."""

from __future__ import annotations

import json
from typing import Iterator

import httpx

from .base import Message


class OllamaBackend:
    def __init__(self, model: str = "llama3.2", url: str = "http://localhost:11434"):
        self.model = model
        self.url = url.rstrip("/")
        self._client = httpx.Client(timeout=120.0)

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass

    @property
    def name(self) -> str:
        return f"ollama/{self.model}"

    def is_available(self) -> bool:
        try:
            r = self._client.get(f"{self.url}/api/tags")
            return r.status_code == 200
        except httpx.ConnectError:
            return False

    def _to_api(self, messages: list[Message]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def chat(self, messages: list[Message], temperature: float = 0.7) -> str:
        r = self._client.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": self._to_api(messages),
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    def stream(self, messages: list[Message], temperature: float = 0.7) -> Iterator[str]:
        with self._client.stream(
            "POST",
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": self._to_api(messages),
                "stream": True,
                "options": {"temperature": temperature},
            },
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if token := data.get("message", {}).get("content", ""):
                        yield token
