"""Speech-to-text and text-to-speech for voice conversations."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

# Whisper model is expensive to load — cache it across calls
_whisper_model = None


def record_audio(duration: int = 5) -> Path:
    """Record audio from microphone. Uses native sample rate to avoid sox warnings."""
    tmpfile = Path(tempfile.mktemp(suffix=".wav"))

    # sox/rec — record at native rate, Whisper handles resampling internally
    try:
        subprocess.run(
            ["rec", "-q", str(tmpfile), "trim", "0", str(duration)],
            check=True,
            timeout=duration + 5,
        )
        return tmpfile
    except FileNotFoundError:
        pass

    # Fallback to ffmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "avfoundation", "-i", ":0",
             "-t", str(duration), "-ac", "1", str(tmpfile)],
            check=True,
            timeout=duration + 5,
            capture_output=True,
        )
        return tmpfile
    except FileNotFoundError:
        raise RuntimeError(
            "No audio recorder found. Install: brew install sox"
        )


def transcribe(audio_path: Path, model: str = "base") -> str:
    """Transcribe audio file using local Whisper model."""
    global _whisper_model
    try:
        import whisper

        # Load model once, reuse across calls
        if _whisper_model is None:
            _whisper_model = whisper.load_model(model)

        result = _whisper_model.transcribe(
            str(audio_path),
            fp16=False,  # CPU doesn't support FP16
        )
        return result["text"].strip()
    except ImportError:
        # Fallback: use whisper CLI
        try:
            result = subprocess.run(
                ["whisper", str(audio_path), "--model", model,
                 "--output_format", "txt", "--output_dir", "/tmp"],
                capture_output=True, text=True, timeout=60,
            )
            txt_path = Path(f"/tmp/{audio_path.stem}.txt")
            if txt_path.exists():
                text = txt_path.read_text().strip()
                txt_path.unlink()
                return text
            return result.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError(
                "Whisper not found. Install: pip install openai-whisper"
            )
    finally:
        audio_path.unlink(missing_ok=True)


def speak(text: str, rate: int = 175) -> None:
    """Speak text aloud using macOS say command."""
    try:
        subprocess.run(
            ["say", "-r", str(rate), text],
            check=True, timeout=300,
        )
    except FileNotFoundError:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", rate)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass


def listen(duration: int = 5, model: str = "base") -> str:
    """Record audio and transcribe it. Returns the transcribed text."""
    audio_path = record_audio(duration=duration)
    return transcribe(audio_path, model=model)
