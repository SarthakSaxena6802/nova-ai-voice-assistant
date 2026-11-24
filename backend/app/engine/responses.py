"""Response templates for the decision engine (clarifications, confirmations, fallbacks)."""
from __future__ import annotations

import re
from typing import Any

INTENT_PHRASES = {
    "GREETING": "say hello",
    "GET_TIME": "tell you the time",
    "GET_DATE": "tell you the date",
    "CALCULATE": "do a calculation",
    "SET_TIMER": "set or manage a timer",
    "CREATE_REMINDER": "create or manage a reminder",
    "OPEN_WEBSITE": "open a website",
    "ASK_QUESTION": "answer a general question",
}

CAPABILITY_SUMMARY = (
    "I can tell the time and date, do calculations, set timers and reminders, open websites, "
    "or answer simple questions."
)

_YES = re.compile(r"^(?:yes|yeah|yep|yup|sure|ok|okay|correct|right|do it|go ahead|please do|affirmative|absolutely|of course|that is right)\b")
_NO = re.compile(r"^(?:no|nope|nah|not really|wrong|negative|do not)\b")
_CANCEL = re.compile(r"^(?:cancel|never ?mind|forget it|stop|abort|nothing|leave it)\b")


def is_yes(text: str) -> bool:
    return bool(_YES.match(text))


def is_no(text: str) -> bool:
    return bool(_NO.match(text))


def is_cancel(text: str) -> bool:
    return bool(_CANCEL.match(text)) and len(text.split()) <= 3


def slot_question(intent: str, slot: str, entities: dict[str, Any], notes: list[str]) -> str:
    if intent == "CREATE_REMINDER" and slot == "time":
        if any("already passed" in n for n in notes):
            return "That time has already passed. When should I remind you instead?"
        if entities.get("message"):
            return "What time should I remind you?"
        return "When should I remind you?"
    return {
        ("SET_TIMER", "duration"): "How long should I set the timer for?",
        ("CREATE_REMINDER", "message"): "What should I remind you about?",
        ("CALCULATE", "expression"): "What would you like me to calculate?",
        ("OPEN_WEBSITE", "website"): "Which website should I open? I can open sites like YouTube, Google, GitHub, Gmail or Spotify.",
    }.get((intent, slot), f"Could you tell me the {slot.replace('_', ' ')}?")


def confirm_question(intent: str, confidence: float) -> str:
    return f"I think you want me to {INTENT_PHRASES.get(intent, intent.lower())}, but I'm only {confidence:.0%} sure. Should I go ahead?"


def low_confidence_message() -> str:
    return f"Sorry, I'm not sure what you meant. Could you rephrase that? {CAPABILITY_SUMMARY}"


def unsupported_message() -> str:
    return f"Sorry, that's not something I can do yet. {CAPABILITY_SUMMARY}"
