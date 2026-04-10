"""LLM backend abstraction."""

from .base import Message, LLMBackend
from .ollama_backend import OllamaBackend
from .openai_backend import OpenAIBackend
from .router import get_backend

__all__ = ["Message", "LLMBackend", "OllamaBackend", "OpenAIBackend", "get_backend"]
