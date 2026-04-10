"""Simple task scheduler for automated routines (e.g., daily briefing)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from rich.console import Console


@dataclass
class ScheduledTask:
    name: str
    func: Callable
    cron_hour: int
    cron_minute: int = 0
    last_run: str | None = None
    enabled: bool = True


class Scheduler:
    """Run tasks at specified times. Designed for a single-user local assistant."""

    def __init__(self, console: Console | None = None):
        self.tasks: list[ScheduledTask] = []
        self.console = console or Console()
        self._running = False
        self._thread: threading.Thread | None = None

    def add(self, name: str, func: Callable, hour: int, minute: int = 0) -> None:
        self.tasks.append(ScheduledTask(
            name=name, func=func, cron_hour=hour, cron_minute=minute
        ))

    def remove(self, name: str) -> bool:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.name != name]
        return len(self.tasks) < before

    def list_tasks(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "schedule": f"{t.cron_hour:02d}:{t.cron_minute:02d}",
                "last_run": t.last_run or "never",
                "enabled": t.enabled,
            }
            for t in self.tasks
        ]

    def _check_and_run(self) -> None:
        now = datetime.now()
        for task in self.tasks:
            if not task.enabled:
                continue
            if now.hour == task.cron_hour and now.minute == task.cron_minute:
                today = now.strftime("%Y-%m-%d")
                if task.last_run == today:
                    continue  # Already ran today
                self.console.print(f"[bold]Running scheduled task: {task.name}[/bold]")
                try:
                    task.func()
                    task.last_run = today
                except Exception as e:
                    self.console.print(f"[red]Task {task.name} failed: {e}[/red]")

    def _loop(self) -> None:
        while self._running:
            self._check_and_run()
            time.sleep(30)  # Check every 30 seconds

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        if self.tasks:
            self.console.print(
                f"[dim]Scheduler started with {len(self.tasks)} task(s)[/dim]"
            )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
