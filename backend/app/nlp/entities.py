"""Entity extraction service.

Intent classification decides *what* the user wants; this module decides the *parameters*.
Each intent has a deterministic extractor that returns the entities it found and the
names of required slots that are still missing (which drives clarification questions).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.core.timeutils import humanize_seconds
from app.nlp.datetime_parser import parse_datetime, remove_spans
from app.nlp.duration import extract_duration
from app.nlp.math_expression import build_expression
from app.nlp.websites import find_website


@dataclass
class EntityResult:
    entities: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text) is not None


# ----------------------------------------------------------------------------- timers
_CANCEL = r"\b(cancel|stop|delete|remove|clear|kill|turn off|end|abort|dismiss)\b"
_STATUS = r"\b(how much time|how long|time left|left on|remaining|status|check|list|show|what timers|any timers)\b"


def extract_timer(text: str, now: datetime) -> EntityResult:
    res = EntityResult()
    if _has(_CANCEL, text) and not _has(r"\bset\b|\bstart\b", text):
        res.entities["operation"] = "cancel"
        res.entities["scope"] = "all" if _has(r"\ball\b|\btimers\b", text) else "latest"
        return res
    if _has(_STATUS, text) and not extract_duration(text):
        res.entities["operation"] = "status"
        return res
    res.entities["operation"] = "create"
    dur = extract_duration(text)
    if dur:
        res.entities["duration_seconds"] = dur.seconds
        res.entities["duration_text"] = humanize_seconds(dur.seconds)
    else:
        res.missing.append("duration")
    label = re.search(r"\b(?:called|named|labell?ed|for (?:the |my )?)([a-z][a-z ]{1,30}?)(?: timer)?$", text)
    if label and not extract_duration(label.group(1)) and label.group(1).strip() not in ("a", "an", "the", "me"):
        res.entities["label"] = label.group(1).strip().capitalize()
    else:
        pre = re.search(r"\b(?:a|an|the|my)\s+([a-z]+)\s+timer\b", text)
        if pre and pre.group(1) not in ("new", "quick", "short", "long", "count", "countdown"):
            res.entities["label"] = pre.group(1).capitalize()
    return res


# -------------------------------------------------------------------------- reminders
_REMINDER_TRIGGERS = [
    r"^(?:please\s+)?(?:can you\s+|could you\s+|would you\s+)?(?:please\s+)?",
    r"\b(?:set|create|make|add|schedule|new)\s+(?:a\s+|an\s+|my\s+)?(?:new\s+)?(?:reminder|alarm)s?(?:\s+for)?\b",
    r"\bremind(?:ed)?\s+me\b|\bremined\s+me\b",
    r"\b(?:i\s+)?(?:need|have|want)\s+to\s+remember\b",
    r"\bmake\s+sure\s+i\s+remember\b|\bdo not let me forget\b|\bnote to self\b|\bremember\b",
    r"\breminder\b|\balarm\b",
    r"\bwake\s+me(?:\s+up)?\b",
]
_LEADING_CONNECTORS = re.compile(r"^(?:to|about|that|of|for|on|at|by|i|me|please|my\s+(?=meeting|appointment))\s+")
_TRAILING_CONNECTORS = re.compile(r"\s+(?:at|on|by|for|in|to|please)$")


def _reminder_message(text: str, spans: list[tuple[int, int]]) -> str:
    msg = remove_spans(text, spans)
    for pattern in _REMINDER_TRIGGERS:
        msg = re.sub(pattern, " ", msg).strip()
    msg = re.sub(r"\s+", " ", msg)
    for _ in range(3):
        msg = _LEADING_CONNECTORS.sub("", msg).strip()
        msg = _TRAILING_CONNECTORS.sub("", msg).strip()
    return msg


def extract_reminder(text: str, now: datetime) -> EntityResult:
    res = EntityResult()
    if _has(r"\b(list|show|what are|what reminders|which reminders|any reminders|read|tell me)\b", text) and not _has(
        r"\bremind me to\b", text
    ):
        res.entities["operation"] = "list"
        return res
    if _has(r"\b(mark|finished|completed|done|complete)\b", text) and _has(r"reminder", text):
        res.entities["operation"] = "complete"
        res.entities["target"] = _target_words(text)
        return res
    if _has(r"\b(delete|remove|cancel|clear|dismiss)\b", text) and _has(r"reminder", text):
        res.entities["operation"] = "delete"
        res.entities["scope"] = "all" if _has(r"\ball\b", text) else "one"
        res.entities["target"] = _target_words(text)
        return res

    res.entities["operation"] = "create"
    dt = parse_datetime(text, now)
    message = _reminder_message(text, dt.spans)
    if not message and _has(r"\balarm\b|\bwake me\b", text):
        message = "Alarm"
    if message:
        res.entities["message"] = message
    else:
        res.missing.append("message")
    if dt.when and dt.in_past:
        res.entities["date"] = dt.when.date().isoformat()
        res.missing.append("time")
        res.notes.append("The requested time has already passed")
    elif dt.when:
        res.entities["due_at"] = dt.when.isoformat()
        res.entities["date"] = dt.when.date().isoformat()
        res.entities["time"] = dt.when.strftime("%H:%M")
    elif dt.has_date and dt.date:
        res.entities["date"] = dt.date.isoformat()
        res.missing.append("time")
    else:
        res.missing.append("time")
    res.notes.extend(dt.notes)
    return res


def _target_words(text: str) -> str:
    m = re.search(r"\b(?:about|to|for|called)\s+(.+)$", text)
    return m.group(1).replace("reminder", "").strip() if m else ""


# --------------------------------------------------------------------------- calculate
def extract_calculation(text: str, now: datetime) -> EntityResult:
    res = EntityResult()
    expr = build_expression(text)
    if expr is None:
        res.missing.append("expression")
        return res
    res.entities.update(expression=expr.expression, operation=expr.operation, operands=expr.operands)
    return res


# ------------------------------------------------------------------------------ website
def extract_website(text: str, now: datetime) -> EntityResult:
    res = EntityResult()
    site = find_website(text)
    if site:
        res.entities.update(website=site.name, website_key=site.key, url=site.url)
    else:
        res.missing.append("website")
    return res


# ------------------------------------------------------------------------- date / time
def extract_date(text: str, now: datetime) -> EntityResult:
    res = EntityResult()
    if "day after tomorrow" in text:
        res.entities["offset_days"] = 2
    elif "tomorrow" in text:
        res.entities["offset_days"] = 1
    elif "yesterday" in text:
        res.entities["offset_days"] = -1
    res.entities["focus"] = (
        "weekday" if _has(r"\bwhat day\b|\bwhich day\b|\bday of the week\b|\bweekend\b|\bis today\b", text)
        else "month" if _has(r"\bmonth\b", text)
        else "year" if _has(r"\byear\b", text)
        else "date"
    )
    return res


def extract_question(text: str, now: datetime) -> EntityResult:
    topic = re.sub(
        r"^(?:can you |could you |please )?(?:explain|tell me about|tell me|what is|what are|who is|who was|"
        r"define|describe|how does|how do|why is|why do|why does)\s+",
        "",
        text,
    ).strip()
    return EntityResult(entities={"question": text, "topic": topic or text})


def _no_entities(text: str, now: datetime) -> EntityResult:
    return EntityResult()


EXTRACTORS: dict[str, Callable[[str, datetime], EntityResult]] = {
    "SET_TIMER": extract_timer,
    "CREATE_REMINDER": extract_reminder,
    "CALCULATE": extract_calculation,
    "OPEN_WEBSITE": extract_website,
    "GET_DATE": extract_date,
    "ASK_QUESTION": extract_question,
}


def extract_entities(intent: str, text: str, now: datetime) -> EntityResult:
    return EXTRACTORS.get(intent, _no_entities)(text, now)
