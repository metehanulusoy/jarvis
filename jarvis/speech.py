"""Speech-to-text using local Whisper model."""

from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path


def record_audio(duration: int = 5, sample_rate: int = 16000) -> Path:
    """Record audio from microphone using macOS rec/sox or ffmpeg."""
    tmpfile = Path(tempfile.mktemp(suffix=".wav"))

    # Try sox first (brew install sox)
    try:
        subprocess.run(
            ["rec", "-q", "-r", str(sample_rate), "-c", "1", "-b", "16",
             str(tmpfile), "trim", "0", str(duration)],
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
             "-t", str(duration), "-ar", str(sample_rate),
             "-ac", "1", str(tmpfile)],
            check=True,
            timeout=duration + 5,
            capture_output=True,
        )
        return tmpfile
    except FileNotFoundError:
        raise RuntimeError(
            "No audio recorder found. Install sox (brew install sox) "
            "or ffmpeg (brew install ffmpeg)."
        )


def transcribe(audio_path: Path, model: str = "base") -> str:
    """Transcribe audio file using local Whisper model."""
    try:
        import whisper
        model_obj = whisper.load_model(model)
        result = model_obj.transcribe(str(audio_path))
        return result["text"].strip()
    except ImportError:
        # Fallback: use whisper CLI if installed
        try:
            result = subprocess.run(
                ["whisper", str(audio_path), "--model", model,
                 "--output_format", "txt", "--output_dir", "/tmp"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            txt_path = Path(f"/tmp/{audio_path.stem}.txt")
            if txt_path.exists():
                text = txt_path.read_text().strip()
                txt_path.unlink()
                return text
            return result.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError(
                "Whisper not found. Install with: pip install openai-whisper"
            )
    finally:
        # Clean up audio file
        audio_path.unlink(missing_ok=True)


def listen(duration: int = 5, model: str = "base") -> str:
    """Record audio and transcribe it. Returns the transcribed text."""
    audio_path = record_audio(duration=duration)
    return transcribe(audio_path, model=model)
