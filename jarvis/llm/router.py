"""Route between Ollama and OpenAI backends."""

from __future__ import annotations

from ..config import Config
from .ollama_backend import OllamaBackend
from .openai_backend import OpenAIBackend
from .base import LLMBackend


def get_backend(cfg: Config, prefer_cloud: bool = False) -> LLMBackend:
    """Return the best available LLM backend.

    Tries Ollama first (local), falls back to OpenAI if configured.
    Set prefer_cloud=True to skip Ollama and go straight to OpenAI.
    """
    ollama = OllamaBackend(model=cfg.ollama.model, url=cfg.ollama.url)
    openai = OpenAIBackend(model=cfg.openai.model, api_key=cfg.openai.api_key)

    if prefer_cloud and openai.is_available():
        return openai

    if ollama.is_available():
        return ollama

    if openai.is_available():
        return openai

    return ollama
