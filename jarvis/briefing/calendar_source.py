"""Read calendar events from ICS files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..config import CalendarConfig


@dataclass
class CalendarEvent:
    summary: str
    start: str
    end: str
    location: str


def fetch_events(cfg: CalendarConfig) -> list[CalendarEvent]:
    """Get today's events from an ICS file."""
    if cfg.type != "ics" or not cfg.path or not cfg.path.exists():
        return []

    try:
        from icalendar import Calendar

        cal = Calendar.from_ical(cfg.path.read_bytes())
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        events = []

        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            dtstart = component.get("dtstart")
            if not dtstart:
                continue
            dt = dtstart.dt
            event_date = dt.date() if hasattr(dt, "date") else dt

            if today <= event_date < tomorrow:
                dtend = component.get("dtend")
                end_str = str(dtend.dt) if dtend else ""
                events.append(CalendarEvent(
                    summary=str(component.get("summary", "Untitled")),
                    start=str(dt),
                    end=end_str,
                    location=str(component.get("location", "")),
                ))

        events.sort(key=lambda e: e.start)
        return events
    except Exception as e:
        return [CalendarEvent(summary=f"Error: {e}", start="", end="", location="")]
