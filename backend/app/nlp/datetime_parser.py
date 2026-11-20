"""Deterministic date/time parser for reminders.

Understands phrases such as::

    "at 8 pm", "at 7:30", "8 30 am", "at 5" (→ next 5 o'clock that is in the future),
    "tomorrow", "day after tomorrow", "tonight", "this evening", "tomorrow morning",
    "on monday", "next friday", "on 25 december", "december 25th", "on the 25th",
    "noon", "midnight", "half past 7", "quarter to 9", "in 2 hours", "in 3 days"

It works on text already normalised by ``normalize_text`` (lower-case, numbers as digits).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from app.nlp.duration import extract_duration

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
PERIODS = {"morning": (9, "am"), "afternoon": (15, "pm"), "evening": (19, "pm"), "night": (20, "pm")}

_RELATIVE = re.compile(
    r"\b(?:in|after)\s+((?:\d+(?:\.\d+)?\s*(?:hours?|hrs?|minutes?|mins?|seconds?|secs?)|an?\s+(?:hour|minute)|half\s+an?\s+hour)"
    r"(?:\s+and\s+(?:\d+(?:\.\d+)?\s*(?:minutes?|mins?|seconds?|secs?)|a\s+half))?)\b"
)
_RELATIVE_DAYS = re.compile(r"\bin\s+(\d+|a|an)\s+(days?|weeks?)\b")
_DAY_AFTER = re.compile(r"\b(?:the\s+)?day\s+after\s+tomorrow\b")
_TOMORROW = re.compile(r"\b(?:tomorrow|tomorow|tommorow|tmrw|tomorrows)\b")
_TODAY = re.compile(r"\btoday\b")
_TONIGHT = re.compile(r"\btonight\b")
_PERIOD = re.compile(r"\b(?:(this|tomorrow|in\s+the|at)\s+)?(morning|afternoon|evening|night)\b")
_WEEKDAY = re.compile(r"\b(?:on\s+)?(?:(next|this|coming)\s+)?(" + "|".join(WEEKDAYS) + r")\b")
_DAY_MONTH = re.compile(r"\b(?:on\s+)?(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + _MONTH_RE + r")\b")
_MONTH_DAY = re.compile(r"\b(?:on\s+)?(" + _MONTH_RE + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b")
_ORDINAL_DAY = re.compile(r"\b(?:on\s+)?the\s+(\d{1,2})(?:st|nd|rd|th)\b")

_NOON = re.compile(r"\b(?:at\s+)?(noon|midday|midnight)\b")
_PAST_TO = re.compile(r"\b(?:at\s+)?(half|quarter|\d{1,2})\s+(past|to)\s+(\d{1,2})\b(?:\s*(am|pm)\b)?")
_TIME_PATTERNS = [
    re.compile(r"\b(?:at\s+|by\s+)?(\d{1,2})[:\s](\d{2})\s*(am|pm)\b"),
    re.compile(r"\b(?:at\s+|by\s+)?(\d{1,2})()\s*(am|pm)\b"),
    re.compile(r"\b(?:at\s+|by\s+)?(\d{1,2}):(\d{2})\b()"),
    re.compile(r"\b(?:at\s+|by\s+)?(\d{1,2})\s*oclock\b()()"),
    re.compile(
        r"\b(?:at|by|for)\s+(\d{1,2})(?:\s+(\d{2}))?\b()"
        r"(?!\s*(?:minutes?|mins?|hours?|hrs?|seconds?|secs?|days?|percent|st|nd|rd|th|of))"
    ),
]


@dataclass
class DateTimeMatch:
    when: datetime | None = None
    date: date | None = None
    time: time | None = None
    has_date: bool = False
    has_time: bool = False
    relative: bool = False
    in_past: bool = False
    spans: list[tuple[int, int]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.has_date or self.has_time


def _next_weekday(today: date, weekday: int, modifier: str | None) -> date:
    ahead = (weekday - today.weekday()) % 7
    if ahead == 0 and modifier != "this":
        ahead = 7
    return today + timedelta(days=ahead)


def _month_date(today: date, month: int, day: int) -> date | None:
    for year in (today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate >= today:
            return candidate
    return None


def parse_datetime(text: str, now: datetime) -> DateTimeMatch:
    result = DateTimeMatch()
    today = now.date()

    # ---- relative offsets ("in 2 hours", "in 3 days") ---------------------------------
    m = _RELATIVE.search(text)
    if m:
        dur = extract_duration(m.group(1))
        if dur:
            result.when = now + timedelta(seconds=dur.seconds)
            result.date, result.time = result.when.date(), result.when.time()
            result.has_date = result.has_time = result.relative = True
            result.spans.append(m.span())
            return result
    m = _RELATIVE_DAYS.search(text)
    relative_day: date | None = None
    if m:
        n = 1 if m.group(1) in ("a", "an") else int(m.group(1))
        relative_day = today + timedelta(days=n * (7 if m.group(2).startswith("week") else 1))
        result.spans.append(m.span())

    # ---- date ------------------------------------------------------------------
    the_date: date | None = relative_day
    period_hint: str | None = None  # "am" | "pm"
    default_hour: int | None = None

    def take(match: re.Match[str]) -> None:
        result.spans.append(match.span())

    if the_date is None and (m := _DAY_AFTER.search(text)):
        the_date = today + timedelta(days=2)
        take(m)
    if the_date is None and (m := _TOMORROW.search(text)):
        the_date = today + timedelta(days=1)
        take(m)
    if the_date is None and (m := _DAY_MONTH.search(text)):
        the_date = _month_date(today, MONTHS[m.group(2)], int(m.group(1)))
        take(m)
    if the_date is None and (m := _MONTH_DAY.search(text)):
        the_date = _month_date(today, MONTHS[m.group(1)], int(m.group(2)))
        take(m)
    if the_date is None and (m := _WEEKDAY.search(text)):
        the_date = _next_weekday(today, WEEKDAYS.index(m.group(2)), m.group(1))
        take(m)
    if the_date is None and (m := _ORDINAL_DAY.search(text)):
        day = int(m.group(1))
        for offset in (0, 1, 2):
            month = (today.month - 1 + offset) % 12 + 1
            year = today.year + (today.month - 1 + offset) // 12
            try:
                cand = date(year, month, day)
            except ValueError:
                continue
            if cand >= today:
                the_date = cand
                break
        take(m)
    if (m := _TODAY.search(text)):
        the_date = the_date or today
        take(m)
    if (m := _TONIGHT.search(text)):
        the_date = the_date or today
        period_hint, default_hour = "pm", 20
        take(m)
    if (m := _PERIOD.search(text)):
        hour, hint = PERIODS[m.group(2)]
        period_hint, default_hour = hint, hour
        take(m)
        if m.group(1) == "this":
            the_date = the_date or today

    # ---- time ------------------------------------------------------------------
    hour: int | None = None
    minute = 0
    meridiem: str | None = None

    if (m := _NOON.search(text)):
        hour = {"noon": 12, "midday": 12, "midnight": 0}[m.group(1)]
        meridiem = "fixed"
        take(m)
    elif (m := _PAST_TO.search(text)):
        amount = {"half": 30, "quarter": 15}.get(m.group(1))
        amount = amount if amount is not None else int(m.group(1))
        base = int(m.group(3))
        if m.group(2) == "past":
            hour, minute = base, amount
        else:
            hour, minute = (base - 1) % 24, 60 - amount
        meridiem = m.group(4)
        take(m)
    else:
        for pattern in _TIME_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue
            h = int(m.group(1))
            mm = int(m.group(2)) if m.group(2) else 0
            if h > 23 or mm > 59:
                continue
            hour, minute = h, mm
            if m.group(3) in ("am", "pm"):
                meridiem = m.group(3)
            take(m)
            break

    if hour is None and default_hour is not None:
        hour, meridiem = default_hour, "fixed"
        result.notes.append(f"Interpreted the time of day as {default_hour % 12 or 12} {'AM' if default_hour < 12 else 'PM'}")

    if hour is not None:
        if meridiem in ("am", "pm"):
            if hour > 12:
                pass  # "15 pm" – treat as 24h
            elif meridiem == "pm" and hour < 12:
                hour += 12
            elif meridiem == "am" and hour == 12:
                hour = 0
        elif meridiem is None and 1 <= hour <= 12:
            if period_hint == "pm" and hour < 12:
                hour += 12
            elif period_hint == "am":
                hour = 0 if hour == 12 else hour
            elif the_date in (None, today):
                # pick the next future occurrence: "at 5" at 10:00 → 17:00
                candidates = [hour % 12, hour % 12 + 12]
                future = [h for h in candidates if datetime.combine(today, time(h, minute)) > now]
                if future:
                    hour = future[0]
                    result.notes.append(f"Assumed {'AM' if hour < 12 else 'PM'} (next upcoming {hour % 12 or 12} o'clock)")
                else:
                    hour = hour % 12 if hour >= 7 else hour % 12 + 12
            else:
                hour = hour + 12 if hour <= 6 else hour % 12 if hour == 12 else hour
                if hour == 0:
                    hour = 12
                result.notes.append(f"Assumed {'AM' if hour < 12 else 'PM'} for an unspecified time")
        result.time = time(hour % 24, minute)
        result.has_time = True

    if the_date is not None:
        result.date = the_date
        result.has_date = True

    # ---- combine -----------------------------------------------------------------
    if result.has_time:
        day = result.date or today
        when = datetime.combine(day, result.time)  # type: ignore[arg-type]
        if when <= now and not result.has_date:
            when += timedelta(days=1)
            result.notes.append("That time has passed today, so I scheduled it for tomorrow")
            result.date = when.date()
        result.when = when
        result.in_past = when <= now
    return result


def remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    keep = [True] * len(text)
    for a, b in spans:
        for i in range(a, b):
            keep[i] = False
    return re.sub(r"\s+", " ", "".join(c if k else " " for c, k in zip(text, keep))).strip()
