"""Text normalisation shared by training and inference.

Two levels:

* ``normalize_text``      – human-readable normalised text used by entity extractors
                             (lower-case, contractions expanded, number words -> digits,
                             wake word removed, punctuation cleaned).
* ``prepare_for_classifier`` – what the ML model actually sees: the normalised text with
                             numbers replaced by a ``<num>`` placeholder so that
                             "timer for 7 minutes" and "timer for 45 minutes" look identical
                             to the classifier. This improves generalisation on a small dataset.
"""
from __future__ import annotations

import re
import unicodedata

from app.nlp.numbers import words_to_numbers

_CONTRACTIONS = {
    "what's": "what is", "whats": "what is", "it's": "it is", "that's": "that is",
    "there's": "there is", "how's": "how is", "where's": "where is", "who's": "who is",
    "i'm": "i am", "im": "i am", "you're": "you are", "we're": "we are", "they're": "they are",
    "i've": "i have", "i'd": "i would", "i'll": "i will", "you'll": "you will",
    "can't": "cannot", "won't": "will not", "don't": "do not", "doesn't": "does not",
    "didn't": "did not", "isn't": "is not", "aren't": "are not", "let's": "let us",
    "o'clock": "oclock",
}

# "hey nova", "ok nova", "nova," at the very beginning of an utterance
_WAKE_WORD = re.compile(r"^\s*(?:(?:hey|hi|ok|okay|yo)\s+)?nova\b[\s,.!:;-]*", re.IGNORECASE)
_TRAILING_NAME = re.compile(r"[\s,]+nova\s*[.!?]*\s*$", re.IGNORECASE)
_NUMBER = re.compile(r"\d+(?:[.:]\d+)?")


def strip_wake_word(text: str) -> str:
    """Remove a leading/trailing "Nova" address unless that is the whole utterance."""
    stripped = _WAKE_WORD.sub("", text, count=1)
    stripped = _TRAILING_NAME.sub("", stripped)
    return stripped if stripped.strip() else text


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.lower().strip()
    text = strip_wake_word(text)

    # a.m. / p.m. variants -> am / pm
    text = re.sub(r"\b([ap])\.\s?m\.?", r"\1m", text)
    text = re.sub(r"(\d)\s*([ap])m\b", r"\1 \2m", text)

    # contractions
    def _expand(match: re.Match[str]) -> str:
        word = match.group(0)
        return _CONTRACTIONS.get(word, word)

    text = re.sub(r"[a-z]+'[a-z]+|\b(?:whats|im)\b", _expand, text)
    text = re.sub(r"\b([a-z]+)'s\b", r"\1s", text)  # possessives: "today's" -> "todays"

    # hyphens next to letters are word joiners ("5-minute", "twenty-five"), not minus signs
    text = re.sub(r"(?<=[a-z])-|-(?=[a-z])", " ", text)
    # symbols that matter for arithmetic get surrounding spaces
    text = re.sub(r"(?<=\d)([+*/^×÷x])(?=\d)", r" \1 ", text)
    text = text.replace("×", " * ").replace("÷", " / ")
    text = re.sub(r"(?<=\d)%", " percent", text)
    text = re.sub(r"(?<=\d)-(?=\d)", " - ", text)

    # keep letters, digits and arithmetic symbols; drop other punctuation
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)
    text = re.sub(r"(?<!\d):|:(?!\d)", " ", text)
    text = re.sub(r"[^a-z0-9+\-*/^().:% ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    text = words_to_numbers(text)
    return text


def prepare_for_classifier(text: str) -> str:
    """Input representation for the intent classifier."""
    normalized = normalize_text(text)
    return _NUMBER.sub(" <num> ", normalized).replace("  ", " ").strip()
