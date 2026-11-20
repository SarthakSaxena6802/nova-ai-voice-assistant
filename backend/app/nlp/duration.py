"""Duration extraction: '10 minutes', '1 hour and 30 minutes', 'half an hour', '90 sec'."""
from __future__ import annotations

import re
from dataclasses import dataclass

_UNIT_SECONDS = {
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
}
_UNIT = r"(hours?|hrs?|hr|h|minutes?|mins?|min|m|seconds?|secs?|sec|s)\b"

# Order matters: more specific phrases first. Each entry: (pattern, seconds-calculator)
_SPECIAL = [
    (re.compile(r"\b(\d+(?:\.\d+)?)\s+and\s+a\s+half\s+" + _UNIT), lambda m: (float(m.group(1)) + 0.5) * _UNIT_SECONDS[m.group(2)]),
    (re.compile(r"\ban?\s+hour\s+and\s+a\s+half\b"), lambda m: 5400),
    (re.compile(r"\b(?:a\s+)?half\s+(?:an?\s+)?hour\b"), lambda m: 1800),
    (re.compile(r"\b(?:a\s+)?quarter\s+(?:of\s+)?(?:an?\s+)?hour\b"), lambda m: 900),
    (re.compile(r"\bhalf\s+(?:a\s+)?minute\b"), lambda m: 30),
    (re.compile(r"\b(?:a\s+)?couple\s+(?:of\s+)?(minutes?|hours?|seconds?)\b"), lambda m: 2 * _UNIT_SECONDS[m.group(1)]),
    (re.compile(r"\b(\d+(?:\.\d+)?)\s*" + _UNIT), lambda m: float(m.group(1)) * _UNIT_SECONDS[m.group(2)]),
    (re.compile(r"\b(?:an?|one)\s+(hour|minute|second)\b"), lambda m: _UNIT_SECONDS[m.group(1)]),
]

_BARE_NUMBER = re.compile(r"\b(\d+(?:\.\d+)?)\b")


@dataclass
class DurationMatch:
    seconds: int
    text: str
    spans: list[tuple[int, int]]


def extract_duration(text: str) -> DurationMatch | None:
    """Sum every duration expression in *text*. Returns None when nothing is found."""
    taken = [False] * len(text)
    total = 0.0
    spans: list[tuple[int, int]] = []
    for pattern, calc in _SPECIAL:
        for m in pattern.finditer(text):
            if any(taken[m.start():m.end()]):
                continue
            total += calc(m)
            spans.append((m.start(), m.end()))
            for i in range(m.start(), m.end()):
                taken[i] = True
    if total <= 0:
        return None
    spans.sort()
    return DurationMatch(seconds=int(round(total)), text=" ".join(text[a:b] for a, b in spans), spans=spans)


def bare_number(text: str) -> float | None:
    """For follow-ups such as 'make it 15' (unit inherited from context)."""
    m = _BARE_NUMBER.search(text)
    return float(m.group(1)) if m else None
