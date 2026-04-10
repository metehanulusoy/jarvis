# Jarvis

A privacy-focused personal AI assistant that runs locally on your hardware using [Ollama](https://ollama.ai). Talk to it with your voice, get morning briefings, research anything, or let it write and run code for you — all without sending data to the cloud.

https://github.com/user-attachments/assets/placeholder

## Features

- **Voice Conversations** — Talk to Jarvis like a real assistant. It listens (Whisper STT), thinks (local LLM), and speaks back (TTS). Just say `/voice`.
- **Local-first** — Runs entirely on your machine with Ollama. No data leaves your computer unless you explicitly enable cloud fallback.
- **Morning Briefing** — Spoken daily summary of your email, calendar, and news headlines.
- **Research Assistant** — Web search (DuckDuckGo) + local document RAG with cited sources.
- **Coding Assistant** — LLM-guided code generation with sandboxed execution and resource limits.
- **Conversation Memory** — Persistent session history across restarts (SQLite). Pick up where you left off.
- **Task Scheduler** — Automated daily briefing at your configured time.
- **Cloud Fallback** — Optional OpenAI integration when local models aren't enough. Use `--cloud` flag.

## Quick Start

```bash
# 1. Clone & install
git clone https://github.com/metehanulusoy/jarvis.git
cd jarvis
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Install Ollama & pull a model
brew install ollama
brew services start ollama
ollama pull llama3.2

# 3. Run
jarvis
```

### Optional: Voice support

```bash
brew install sox                   # microphone recording
pip install openai-whisper         # speech-to-text
```

### Optional: One-command launch from anywhere

Add this to your `~/.zshrc` or `~/.bashrc`:

```bash
alias jarvis="source ~/jarvis/.venv/bin/activate && cd ~/jarvis && python3 -m jarvis.cli"
```

Then just type `jarvis` from any terminal.

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
| `/voice` | **Start voice conversation** — talk and listen hands-free |
| `/briefing` | Run morning briefing with spoken output |
| `/research <query>` | Search web + local docs, get cited summary |
| `/web <query>` | Web-only search |
| `/docs <query>` | Local documents only |
| `/code <task>` | Coding assistant with sandboxed code execution |
| `/listen` | Single voice input (one question) |
| `/history` | Show recent conversation |
| `/sessions` | List all saved sessions |
| `/clear` | Clear current session history |
| `/quit` | Exit |

### Voice Mode

Type `/voice` and start talking. Jarvis will:

1. **Listen** to your microphone (6 seconds per turn)
2. **Transcribe** your speech locally with Whisper
3. **Think** and generate a response with the local LLM
4. **Speak** the answer back to you
5. **Repeat** — it's a continuous conversation

Say "exit", "quit", or "goodbye" to return to text mode.

### Standalone Commands

```bash
jarvis briefing            # morning briefing
jarvis research "query"    # research a topic
jarvis code "task"         # coding help
jarvis index               # index documents for RAG
jarvis listen              # transcribe speech
jarvis voice               # voice conversation
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
      - "https://feeds.arstechnica.com/arstechnica/index"
  tts:
    engine: "say"              # "say" (macOS) or "pyttsx3" (cross-platform)

research:
  documents_dir: "~/jarvis/data/documents"
  embedding_model: "all-MiniLM-L6-v2"
  top_k: 5

coding:
  timeout: 30
  allowed_dirs:
    - "~/jarvis/data"
    - "~"
```

**Credentials are never stored in config files** — only environment variable names.

```bash
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"   # Gmail App Password
export OPENAI_API_KEY="sk-..."                      # optional
```

## Document Search (RAG)

Drop files into `data/documents/` and index them:

```bash
jarvis index
```

Supported formats: PDF, TXT, Markdown. Uses ChromaDB + sentence-transformers for semantic search with incremental re-indexing.

Then search with `/docs <query>` or `/research <query>` (combines web + local docs).

## Architecture

```
jarvis/
├── cli.py              # Entry point, REPL, command routing, voice mode
├── config.py           # YAML config loader (secrets from env vars only)
├── sessions.py         # SQLite conversation persistence
├── scheduler.py        # Background task scheduler (cron-style)
├── speech.py           # Whisper STT + sox recording + macOS TTS
├── llm/
│   ├── base.py         # LLM protocol definition
│   ├── ollama_backend.py   # Local inference via Ollama
│   ├── openai_backend.py   # Cloud fallback via OpenAI
│   └── router.py       # Auto-selects best available backend
├── briefing/
│   ├── email_source.py # Gmail IMAP with SSL validation
│   ├── calendar_source.py  # ICS file parser
│   ├── news_source.py  # RSS feed aggregator
│   ├── tts.py          # Text-to-speech output
│   └── briefing.py     # Orchestrates sources + LLM summary + speech
├── research/
│   ├── web_search.py   # DuckDuckGo search
│   ├── doc_index.py    # ChromaDB + sentence-transformers RAG pipeline
│   └── research.py     # Orchestrates search + RAG + cited summary
├── coding/
│   ├── sandbox.py      # Subprocess execution with resource limits
│   ├── file_ops.py     # Scoped file access with symlink protection
│   └── coding.py       # LLM-guided code generation & execution
└── utils/
    └── text.py         # Chunking, PDF extraction, prompt injection sanitization
```

## Security

- API keys and passwords are **never stored in files** — only env var references
- Code execution runs in a **subprocess sandbox** with resource limits (memory, disk, CPU)
- Sensitive env vars (API keys, passwords) are **stripped** from sandbox environment
- File operations are **scoped** to configured directories; symlink writes are blocked
- External data (emails, web results) is **sanitized** with prompt injection detection before passing to the LLM
- IMAP connections use **explicit SSL certificate validation**
- Dependency versions are **pinned to major ranges** to prevent supply chain attacks

## Requirements

- **Python** 3.11+
- **Ollama** with any model (default: `llama3.2`)
- **macOS** recommended (uses `say` for TTS, `avfoundation` for audio)
- **sox** for voice input (`brew install sox`)
- **Whisper** for STT (`pip install openai-whisper`)

## License

MIT
