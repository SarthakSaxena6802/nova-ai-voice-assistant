"""Time helpers.

Nova is local-first: the backend and the browser run on the same machine, so all
timestamps are stored as naive *local* datetimes. Using one helper everywhere makes
it trivial to freeze time in tests.
"""
from __future__ import annotations

import re
from datetime import datetime


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def humanize_seconds(total: float) -> str:
    """300 -> '5 minutes', 5400 -> '1 hour and 30 minutes'."""
    total = int(round(total))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def duration_adjective(total: float) -> str:
    """300 -> '5-minute', 3 -> '3-second', 5400 -> '1 hour and 30 minutes' (for "your X timer")."""
    text = humanize_seconds(total)
    m = re.fullmatch(r"(\d+) (hour|minute|second)s?", text)
    return f"{m.group(1)}-{m.group(2)}" if m else text


def format_time(dt: datetime) -> str:
    """'7:05 PM'"""
    return dt.strftime("%I:%M %p").lstrip("0")


def format_date(dt: datetime) -> str:
    """'Friday, November 20, 2026'"""
    return f"{dt.strftime('%A')}, {dt.strftime('%B')} {dt.day}, {dt.year}"


def describe_datetime(dt: datetime, reference: datetime | None = None) -> str:
    """Natural description relative to *reference*: 'today at 8:00 PM', 'tomorrow at 9:00 AM'."""
    reference = reference or now()
    delta_days = (dt.date() - reference.date()).days
    if delta_days == 0:
        day = "today"
    elif delta_days == 1:
        day = "tomorrow"
    elif 1 < delta_days < 7:
        day = f"on {dt.strftime('%A')}"
    else:
        day = f"on {dt.strftime('%B')} {dt.day}"
    return f"{day} at {format_time(dt)}"
