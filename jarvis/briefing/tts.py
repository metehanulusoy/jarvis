"""Text-to-speech output."""

from __future__ import annotations

import subprocess

from ..config import TTSConfig


def speak(text: str, cfg: TTSConfig) -> None:
    """Speak text aloud using the configured TTS engine."""
    if cfg.engine == "say":
        _speak_say(text, cfg.rate)
    elif cfg.engine == "pyttsx3":
        _speak_pyttsx3(text, cfg.rate)
    else:
        _speak_say(text, cfg.rate)  # fallback


def _speak_say(text: str, rate: int) -> None:
    """Use macOS built-in 'say' command."""
    try:
        subprocess.run(
            ["say", "-r", str(rate), text],
            check=True,
            timeout=300,
        )
    except FileNotFoundError:
        # Not on macOS — fall back to pyttsx3
        _speak_pyttsx3(text, rate)


def _speak_pyttsx3(text: str, rate: int) -> None:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.say(text)
        engine.runAndWait()
    except Exception:
        pass  # TTS is best-effort
