"""Coding assistant: LLM-guided code generation and execution."""

from __future__ import annotations

import re

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ..config import CodingConfig
from ..llm.base import LLMBackend, Message
from .file_ops import read_file, write_file
from .sandbox import run_code


SYSTEM_PROMPT = """\
You are Jarvis, a coding assistant. Help the user with programming tasks.

You can include executable Python code in your responses using fenced code blocks:
```python
# your code here
```

When the user asks you to run code, write code, or solve a programming problem,
include runnable Python code in a fenced ```python block. The code will be extracted
and executed automatically.

You can also read and write files. To do so, respond with one of:
- READ: <filepath>
- WRITE: <filepath>
<content of file>
END_WRITE

Be concise in your explanations. Focus on working code."""


def run_coding(
    task: str,
    cfg: CodingConfig,
    llm: LLMBackend,
    console: Console,
    history: list[Message] | None = None,
) -> str:
    """Handle a coding task: generate code, optionally execute it."""
    if history is None:
        history = [Message(role="system", content=SYSTEM_PROMPT)]

    history.append(Message(role="user", content=task))

    console.print("[dim]Thinking...[/dim]")
    response = llm.chat(history, temperature=0.3)
    history.append(Message(role="assistant", content=response))

    # Display response
    console.print()
    console.print(response)

    # Extract and offer to run Python code blocks
    code_blocks = re.findall(r"```python\n(.*?)```", response, re.DOTALL)
    for i, code in enumerate(code_blocks):
        console.print()
        console.print(Panel(
            Syntax(code, "python", theme="monokai"),
            title=f"Code Block {i + 1}",
            border_style="blue",
        ))
        console.print("[bold]Run this code? (y/n):[/bold] ", end="")
        choice = input().strip().lower()
        if choice in ("y", "yes"):
            console.print("[dim]Executing...[/dim]")
            result = run_code(code, timeout=cfg.timeout)

            if result.stdout:
                console.print(Panel(result.stdout, title="Output", border_style="green"))
            if result.stderr:
                console.print(Panel(result.stderr, title="Errors", border_style="red"))
            if result.timed_out:
                console.print("[red]Execution timed out.[/red]")

            # Feed result back to LLM
            exec_msg = f"Code execution result:\nReturn code: {result.returncode}\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}"
            history.append(Message(role="user", content=exec_msg))

    # Handle file operations
    _handle_file_ops(response, cfg, console)

    return response


def _handle_file_ops(response: str, cfg: CodingConfig, console: Console) -> None:
    """Parse and execute file read/write commands from LLM response."""
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("READ: "):
            filepath = line[6:].strip()
            content = read_file(filepath, cfg.allowed_dirs)
            console.print(Panel(content[:2000], title=f"File: {filepath}", border_style="cyan"))

    # Handle WRITE blocks
    write_pattern = re.findall(
        r"WRITE:\s*(.+?)\n(.*?)END_WRITE", response, re.DOTALL
    )
    for filepath, content in write_pattern:
        filepath = filepath.strip()
        console.print(f"[bold]Write to {filepath}? (y/n):[/bold] ", end="")
        choice = input().strip().lower()
        if choice in ("y", "yes"):
            result = write_file(filepath, content, cfg.allowed_dirs)
            console.print(f"[green]{result}[/green]")
