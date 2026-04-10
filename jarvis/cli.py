"""Jarvis CLI — personal AI assistant."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import load_config
from .llm import get_backend
from .llm.base import Message
from .sessions import save_message, load_history, list_sessions, clear_session
from .scheduler import Scheduler

console = Console()

BANNER = """[bold cyan]
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
[/bold cyan]"""

SYSTEM_MSG = Message(
    role="system",
    content=(
        "You are Jarvis, a helpful personal AI assistant. "
        "Be concise, clear, and helpful. "
        "You are running locally for privacy."
    ),
)


@click.group(invoke_without_command=True)
@click.option("--config", "-c", default=None, help="Path to config.yaml")
@click.option("--cloud", is_flag=True, help="Prefer OpenAI over local Ollama")
@click.option("--session", "-s", default="default", help="Session name for history")
@click.pass_context
def main(ctx, config, cloud, session):
    """Jarvis — your personal AI assistant."""
    ctx.ensure_object(dict)
    cfg = load_config(config)
    ctx.obj["cfg"] = cfg
    ctx.obj["cloud"] = cloud
    ctx.obj["session"] = session

    if ctx.invoked_subcommand is None:
        _repl(cfg, cloud, session)


def _repl(cfg, cloud, session_name):
    """Interactive chat REPL."""
    llm = get_backend(cfg, prefer_cloud=cloud)

    # Start scheduler with daily briefing
    scheduler = Scheduler(console)
    scheduler.add(
        "morning_briefing",
        lambda: _auto_briefing(cfg, llm),
        hour=8, minute=0,
    )
    scheduler.start()

    console.print(BANNER)
    console.print(f"[dim]Backend: {llm.name} | Session: {session_name}[/dim]")
    console.print("[dim]Commands:[/dim]")
    console.print("[dim]  /briefing  /research <q>  /code <task>  /web <q>  /docs <q>[/dim]")
    console.print("[dim]  /listen    /history       /sessions     /clear    /quit[/dim]")
    console.print()

    # Load previous conversation history
    history = [SYSTEM_MSG]
    prev = load_history(session_name)
    if prev:
        history.extend(prev)
        console.print(f"[dim]Restored {len(prev)} messages from session '{session_name}'[/dim]")

    code_history: list[Message] = []

    while True:
        try:
            user_input = console.input("[bold green]You>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            scheduler.stop()
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye.[/dim]")
            scheduler.stop()
            break

        # --- Voice input ---
        if user_input.lower() == "/listen":
            try:
                from .speech import listen
                console.print("[dim]Listening for 5 seconds...[/dim]")
                user_input = listen(duration=5)
                console.print(f"[bold green]You>[/bold green] {user_input}")
                if not user_input:
                    console.print("[yellow]No speech detected.[/yellow]")
                    continue
            except Exception as e:
                console.print(f"[red]STT error: {e}[/red]")
                continue

        # --- Session commands ---
        if user_input.lower() == "/history":
            msgs = load_history(session_name, limit=20)
            for m in msgs:
                tag = "[green]You[/green]" if m.role == "user" else "[cyan]Jarvis[/cyan]"
                console.print(f"{tag}: {m.content[:120]}")
            continue

        if user_input.lower() == "/sessions":
            sessions = list_sessions()
            if not sessions:
                console.print("[dim]No sessions yet.[/dim]")
            else:
                table = Table(title="Sessions")
                table.add_column("Name")
                table.add_column("Messages")
                table.add_column("Last Active")
                for s in sessions:
                    table.add_row(s["session"], str(s["count"]), s["last_active"][:16])
                console.print(table)
            continue

        if user_input.lower() == "/clear":
            n = clear_session(session_name)
            history = [SYSTEM_MSG]
            console.print(f"[dim]Cleared {n} messages from session '{session_name}'[/dim]")
            continue

        # --- Feature commands ---
        if user_input.lower() == "/briefing":
            from .briefing.briefing import run_briefing
            run_briefing(cfg.briefing, llm, console)
            continue

        if user_input.lower().startswith("/research "):
            query = user_input[10:].strip()
            from .research.research import run_research
            run_research(query, cfg.research, llm, console)
            continue

        if user_input.lower().startswith("/web "):
            query = user_input[5:].strip()
            from .research.research import run_research
            run_research(query, cfg.research, llm, console, use_web=True, use_docs=False)
            continue

        if user_input.lower().startswith("/docs "):
            query = user_input[6:].strip()
            from .research.research import run_research
            run_research(query, cfg.research, llm, console, use_web=False, use_docs=True)
            continue

        if user_input.lower().startswith("/code "):
            task = user_input[6:].strip()
            from .coding.coding import run_coding
            run_coding(task, cfg.coding, llm, console, code_history or None)
            continue

        # --- Regular chat ---
        user_msg = Message(role="user", content=user_input)
        history.append(user_msg)
        save_message(session_name, user_msg)

        try:
            console.print()
            full_response = []
            for token in llm.stream(history):
                console.print(token, end="", highlight=False)
                full_response.append(token)
            console.print()
            console.print()

            assistant_msg = Message(role="assistant", content="".join(full_response))
            history.append(assistant_msg)
            save_message(session_name, assistant_msg)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            history.pop()


def _auto_briefing(cfg, llm):
    """Called by the scheduler for the morning briefing."""
    from .briefing.briefing import run_briefing
    run_briefing(cfg.briefing, llm, console)


@main.command()
@click.pass_context
def briefing(ctx):
    """Run the morning briefing."""
    from .briefing.briefing import run_briefing
    cfg = ctx.obj["cfg"]
    llm = get_backend(cfg, prefer_cloud=ctx.obj["cloud"])
    run_briefing(cfg.briefing, llm, console)


@main.command()
@click.argument("query")
@click.pass_context
def research(ctx, query):
    """Research a topic using web + local documents."""
    from .research.research import run_research
    cfg = ctx.obj["cfg"]
    llm = get_backend(cfg, prefer_cloud=ctx.obj["cloud"])
    run_research(query, cfg.research, llm, console)


@main.command()
@click.argument("task")
@click.pass_context
def code(ctx, task):
    """Get help with a coding task."""
    from .coding.coding import run_coding
    cfg = ctx.obj["cfg"]
    llm = get_backend(cfg, prefer_cloud=ctx.obj["cloud"])
    run_coding(task, cfg.coding, llm, console)


@main.command()
@click.pass_context
def index(ctx):
    """Index local documents for RAG search."""
    from .research.doc_index import DocumentIndex
    cfg = ctx.obj["cfg"]
    idx = DocumentIndex(cfg.research)
    idx.index_documents(console)


@main.command()
@click.option("--duration", "-d", default=5, help="Recording duration in seconds")
@click.pass_context
def listen(ctx, duration):
    """Transcribe speech from microphone."""
    from .speech import listen as stt_listen
    console.print(f"[dim]Listening for {duration} seconds...[/dim]")
    try:
        text = stt_listen(duration=duration)
        console.print(f"[bold]Transcribed:[/bold] {text}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command()
@click.pass_context
def sessions(ctx):
    """List all conversation sessions."""
    all_sessions = list_sessions()
    if not all_sessions:
        console.print("[dim]No sessions yet.[/dim]")
        return
    table = Table(title="Sessions")
    table.add_column("Name")
    table.add_column("Messages")
    table.add_column("Last Active")
    for s in all_sessions:
        table.add_row(s["session"], str(s["count"]), s["last_active"][:16])
    console.print(table)


if __name__ == "__main__":
    main()
