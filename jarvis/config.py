"""Load and validate config.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _expand(p: str) -> Path:
    return Path(p).expanduser().resolve()


def _env(name: str | None) -> str | None:
    if name:
        return os.environ.get(name)
    return None


@dataclass
class OllamaConfig:
    model: str = "llama3.2"
    url: str = "http://localhost:11434"


@dataclass
class OpenAIConfig:
    model: str = "gpt-4o-mini"
    api_key: str | None = None


@dataclass
class EmailConfig:
    imap_server: str = "imap.gmail.com"
    username: str | None = None
    password: str | None = None
    max_emails: int = 20


@dataclass
class CalendarConfig:
    type: str = "ics"
    path: Path | None = None
    url: str | None = None


@dataclass
class NewsConfig:
    feeds: list[str] = field(default_factory=list)
    max_items_per_feed: int = 5


@dataclass
class TTSConfig:
    engine: str = "say"
    rate: int = 175


@dataclass
class BriefingConfig:
    email: EmailConfig = field(default_factory=EmailConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)


@dataclass
class ResearchConfig:
    documents_dir: Path = field(default_factory=lambda: _expand("~/jarvis/data/documents"))
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k: int = 5


@dataclass
class CodingConfig:
    timeout: int = 30
    allowed_dirs: list[Path] = field(default_factory=list)


@dataclass
class Config:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    briefing: BriefingConfig = field(default_factory=BriefingConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)
    coding: CodingConfig = field(default_factory=CodingConfig)


def load_config(path: str | Path | None = None) -> Config:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config.yaml"
    path = Path(path)
    if not path.exists():
        return Config()

    raw = yaml.safe_load(path.read_text()) or {}

    # LLM
    ollama_raw = raw.get("llm", {}).get("ollama", {})
    openai_raw = raw.get("llm", {}).get("openai", {})
    ollama = OllamaConfig(
        model=ollama_raw.get("model", "llama3.2"),
        url=ollama_raw.get("url", "http://localhost:11434"),
    )
    openai_cfg = OpenAIConfig(
        model=openai_raw.get("model", "gpt-4o-mini"),
        api_key=_env(openai_raw.get("api_key_env")),
    )

    # Briefing
    br = raw.get("briefing", {})
    em = br.get("email", {})
    email = EmailConfig(
        imap_server=em.get("imap_server", "imap.gmail.com"),
        username=_env(em.get("username_env")),
        password=_env(em.get("password_env")),
        max_emails=em.get("max_emails", 20),
    )
    cal_raw = br.get("calendar", {})
    calendar = CalendarConfig(
        type=cal_raw.get("type", "ics"),
        path=_expand(cal_raw["path"]) if cal_raw.get("path") else None,
        url=cal_raw.get("url"),
    )
    news_raw = br.get("news", {})
    news = NewsConfig(
        feeds=news_raw.get("feeds", []),
        max_items_per_feed=news_raw.get("max_items_per_feed", 5),
    )
    tts_raw = br.get("tts", {})
    tts = TTSConfig(engine=tts_raw.get("engine", "say"), rate=tts_raw.get("rate", 175))
    briefing = BriefingConfig(email=email, calendar=calendar, news=news, tts=tts)

    # Research
    res = raw.get("research", {})
    research = ResearchConfig(
        documents_dir=_expand(res.get("documents_dir", "~/jarvis/data/documents")),
        embedding_model=res.get("embedding_model", "all-MiniLM-L6-v2"),
        top_k=res.get("top_k", 5),
    )

    # Coding
    cod = raw.get("coding", {})
    coding = CodingConfig(
        timeout=cod.get("timeout", 30),
        allowed_dirs=[_expand(d) for d in cod.get("allowed_dirs", [])],
    )

    return Config(
        ollama=ollama,
        openai=openai_cfg,
        briefing=briefing,
        research=research,
        coding=coding,
    )
