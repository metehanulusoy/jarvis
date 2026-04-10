"""OpenAI cloud LLM backend."""

from __future__ import annotations

from typing import Iterator

from .base import Message


class OpenAIBackend:
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self._api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    @property
    def name(self) -> str:
        return f"openai/{self.model}"

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            self._get_client().models.list()
            return True
        except Exception:
            return False

    def _to_api(self, messages: list[Message]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def chat(self, messages: list[Message], temperature: float = 0.7) -> str:
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=self._to_api(messages),
            temperature=temperature,
        )
        return response.choices[0].message.content

    def stream(self, messages: list[Message], temperature: float = 0.7) -> Iterator[str]:
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=self._to_api(messages),
            temperature=temperature,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
