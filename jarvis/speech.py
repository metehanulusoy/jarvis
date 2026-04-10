"""Speech-to-text and text-to-speech for voice conversations."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

# Cache Whisper model across calls (expensive to load)
_whisper_model = None

# Jarvis voice config — British, deep, calm (closest to Iron Man's JARVIS)
JARVIS_VOICE = "en-GB-RyanNeural"
JARVIS_RATE = "-5%"
JARVIS_PITCH = "-30Hz"


def record_audio(duration: int = 5) -> Path:
    """Record audio from microphone. Uses native sample rate."""
    tmpfile = Path(tempfile.mktemp(suffix=".wav"))

    # sox/rec — record at native rate, Whisper handles resampling
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

        if _whisper_model is None:
            _whisper_model = whisper.load_model(model)

        result = _whisper_model.transcribe(
            str(audio_path),
            fp16=False,
        )
        return result["text"].strip()
    except ImportError:
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
    """Speak text using edge-tts (Jarvis voice), fallback to macOS say."""
    # Try edge-tts first — much better quality, Jarvis-like voice
    try:
        _speak_edge_tts(text)
        return
    except Exception:
        pass

    # Fallback to macOS say
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


def _speak_edge_tts(text: str) -> None:
    """Use Microsoft Edge TTS for high-quality Jarvis-like voice."""
    import edge_tts

    tmpfile = Path(tempfile.mktemp(suffix=".mp3"))
    try:
        async def _generate():
            communicate = edge_tts.Communicate(
                text,
                voice=JARVIS_VOICE,
                rate=JARVIS_RATE,
                pitch=JARVIS_PITCH,
            )
            await communicate.save(str(tmpfile))

        asyncio.run(_generate())

        # Play the audio
        subprocess.run(
            ["afplay", str(tmpfile)],
            check=True, timeout=300,
        )
    finally:
        tmpfile.unlink(missing_ok=True)


def listen(duration: int = 5, model: str = "base") -> str:
    """Record audio and transcribe it. Returns the transcribed text."""
    audio_path = record_audio(duration=duration)
    return transcribe(audio_path, model=model)
