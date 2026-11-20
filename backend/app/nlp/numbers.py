"""Convert spelled-out numbers to digits: 'twenty five' -> '25', 'one hundred and fifty' -> '150'.

Speech recognisers often return number words, so every downstream extractor
(durations, times, arithmetic) works on digits only.
"""
from __future__ import annotations

UNITS = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9,
}
TEENS = {
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000}


def _kind(token: str) -> str | None:
    if token in UNITS and token != "oh":
        return "unit"
    if token in TEENS:
        return "teen"
    if token in TENS:
        return "tens"
    if token in SCALES:
        return "scale"
    return None


def _value(token: str) -> int:
    return UNITS.get(token) or TEENS.get(token) or TENS.get(token) or 0


def _format(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def words_to_numbers(text: str) -> str:
    tokens = text.split()
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        starts_number = _kind(tok) in ("unit", "teen", "tens") or (
            tok == "a" and nxt in ("hundred", "thousand")
        )
        if not starts_number:
            out.append(tok)
            i += 1
            continue

        total, current, last = 0, 0, None
        j = i
        if tok == "a":
            current, last, j = 1, "unit", i + 1
        while j < len(tokens):
            t = tokens[j]
            kind = _kind(t)
            if kind == "unit" and last in (None, "tens", "scale"):
                current += _value(t)
            elif kind in ("teen", "tens") and last in (None, "scale"):
                current += _value(t)
            elif kind == "scale" and last in ("unit", "teen", "tens"):
                scale = SCALES[t]
                if scale == 100:
                    current *= 100
                else:
                    total += current * scale
                    current = 0
            elif t == "and" and last == "scale" and j + 1 < len(tokens) and _kind(tokens[j + 1]) in (
                "unit", "teen", "tens"
            ):
                j += 1
                continue
            else:
                break
            last = kind
            j += 1

        value: float = total + current
        # Decimal part: "two point five" -> 2.5
        if j + 1 < len(tokens) and tokens[j] == "point" and tokens[j + 1] in UNITS:
            digits = ""
            k = j + 1
            while k < len(tokens) and tokens[k] in UNITS:
                digits += str(UNITS[tokens[k]])
                k += 1
            value = float(f"{int(value)}.{digits}")
            j = k
        out.append(_format(value))
        i = j
    return " ".join(out)
