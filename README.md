# Jarvis

A privacy-focused personal AI assistant that runs locally on your hardware using [Ollama](https://ollama.ai).

## Features

- **Local-first** — Runs on your machine with Ollama. No data leaves your computer unless you explicitly enable cloud fallback.
- **Morning Briefing** — Spoken daily summary of your email, calendar, and news via TTS.
- **Research Assistant** — Web search (DuckDuckGo) + local document RAG with citations.
- **Coding Assistant** — LLM-guided code generation with sandboxed execution.
- **Voice Input** — Speech-to-text via Whisper for hands-free interaction.
- **Conversation Memory** — Persistent session history across restarts (SQLite).
- **Task Scheduler** — Automated daily briefing at a configured time.
- **Cloud Fallback** — Optional OpenAI integration for complex queries when local models aren't enough.

## Quick Start

```bash
# 1. Install
cd jarvis
pip install -e .

# 2. Pull a local model
ollama pull llama3.2
ollama serve

# 3. Run
jarvis
```

## Usage

### Interactive Mode

```bash
jarvis                     # start REPL (default session)
jarvis -s work             # start with named session
jarvis --cloud             # prefer OpenAI over Ollama
```

### REPL Commands

| Command | Description |
|---------|-------------|
| `/briefing` | Run morning briefing with TTS |
| `/research <query>` | Search web + local docs, get cited summary |
| `/web <query>` | Web-only search |
| `/docs <query>` | Local documents only |
| `/code <task>` | Coding assistant with code execution |
| `/listen` | Voice input (requires sox or ffmpeg) |
| `/history` | Show recent conversation |
| `/sessions` | List all saved sessions |
| `/clear` | Clear current session history |
| `/quit` | Exit |

### Standalone Commands

```bash
jarvis briefing            # morning briefing
jarvis research "query"    # research a topic
jarvis code "task"         # coding help
jarvis index               # index documents for RAG
jarvis listen              # transcribe speech
jarvis sessions            # list sessions
```

## Configuration

Edit `config.yaml` in the project root:

```yaml
llm:
  ollama:
    model: "llama3.2"          # any Ollama model
  openai:
    api_key_env: "OPENAI_API_KEY"  # env var name, not the key itself

briefing:
  email:
    username_env: "GMAIL_USER"
    password_env: "GMAIL_APP_PASSWORD"
  news:
    feeds:
      - "https://hnrss.org/frontpage"

research:
  documents_dir: "~/jarvis/data/documents"
```

**Credentials are never stored in config files** — only environment variable names.

```bash
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export OPENAI_API_KEY="sk-..."  # optional
```

## Document Search (RAG)

Drop files into `data/documents/` and index them:

```bash
jarvis index
```

Supported formats: PDF, TXT, Markdown. Uses ChromaDB + sentence-transformers for semantic search.

## Voice

**Input** (Speech-to-Text): Requires [Whisper](https://github.com/openai/whisper) and an audio recorder:

```bash
pip install openai-whisper
brew install sox  # or ffmpeg
```

**Output** (Text-to-Speech): Uses macOS `say` by default, or `pyttsx3` as fallback.

## Architecture

```
jarvis/
├── cli.py              # Entry point, REPL, command routing
├── config.py           # YAML config loader
├── sessions.py         # SQLite conversation persistence
├── scheduler.py        # Background task scheduler
├── speech.py           # Whisper STT + audio recording
├── llm/
│   ├── base.py         # LLM protocol definition
│   ├── ollama_backend.py
│   ├── openai_backend.py
│   └── router.py       # Auto-selects best available backend
├── briefing/
│   ├── email_source.py # Gmail IMAP
│   ├── calendar_source.py
│   ├── news_source.py  # RSS feeds
│   ├── tts.py          # Text-to-speech
│   └── briefing.py     # Orchestrator
├── research/
│   ├── web_search.py   # DuckDuckGo
│   ├── doc_index.py    # ChromaDB RAG pipeline
│   └── research.py     # Orchestrator
├── coding/
│   ├── sandbox.py      # Subprocess execution + resource limits
│   ├── file_ops.py     # Scoped file access
│   └── coding.py       # Orchestrator
└── utils/
    └── text.py         # Chunking, PDF extraction, sanitization
```

## Security

- API keys and passwords are **never stored in files** — only env var references
- Code execution runs in a **subprocess sandbox** with resource limits (memory, disk, CPU)
- Sensitive env vars (API keys, passwords) are **stripped** from sandbox environment
- File operations are **scoped** to configured directories; symlink writes are blocked
- External data (emails, web results) is **sanitized** before passing to the LLM
- IMAP connections use **explicit SSL certificate validation**

## License

MIT
