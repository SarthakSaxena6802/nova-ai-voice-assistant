"""Entity extraction tests (durations, reminder date/time/message, calculator, websites)."""
from __future__ import annotations

from datetime import datetime

import pytest

from app.nlp.entities import extract_entities
from app.nlp.math_expression import CalculationError, build_expression, safe_evaluate
from app.nlp.preprocessing import normalize_text
from app.nlp.websites import find_website

NOW = datetime(2026, 11, 20, 10, 0, 0)  # a Friday morning


def ents(intent: str, text: str):
    return extract_entities(intent, normalize_text(text), NOW)


@pytest.mark.parametrize(
    "text,seconds",
    [
        ("set a timer for 10 minutes", 600),
        ("start a 5-minute countdown", 300),
        ("timer for 2 hours", 7200),
        ("remind me in 30 seconds", 30),
        ("set a timer for half an hour", 1800),
        ("set a timer for an hour", 3600),
        ("countdown for one hour and thirty minutes", 5400),
        ("timer for 1 and a half hours", 5400),
        ("set a timer for ninety seconds", 90),
    ],
)
def test_timer_duration(text, seconds):
    r = ents("SET_TIMER", text)
    assert r.entities["operation"] == "create"
    assert r.entities["duration_seconds"] == seconds
    assert not r.missing


def test_timer_missing_duration_and_operations():
    assert ents("SET_TIMER", "set a timer").missing == ["duration"]
    assert ents("SET_TIMER", "cancel my timer").entities["operation"] == "cancel"
    assert ents("SET_TIMER", "cancel all timers").entities["scope"] == "all"
    assert ents("SET_TIMER", "how much time is left on my timer").entities["operation"] == "status"
    assert ents("SET_TIMER", "set a tea timer for 4 minutes").entities["label"] == "Tea"


@pytest.mark.parametrize(
    "text,message,due",
    [
        ("Remind me tomorrow at 9 AM to attend my meeting", "attend my meeting", "2026-11-21T09:00:00"),
        ("remind me to study at 8 pm", "study", "2026-11-20T20:00:00"),
        ("remind me about my meeting at 5", "my meeting", "2026-11-20T17:00:00"),
        ("remind me to take my medicine at 9", "take my medicine", "2026-11-20T21:00:00"),
        ("remind me to check the oven at seven thirty pm", "check the oven", "2026-11-20T19:30:00"),
        ("remind me in 2 hours to stretch", "stretch", "2026-11-20T12:00:00"),
        ("remind me tonight to charge my phone", "charge my phone", "2026-11-20T20:00:00"),
        ("remind me to pay rent on the 25th at noon", "pay rent", "2026-11-25T12:00:00"),
        ("remind me on monday at 10 am to submit the report", "submit the report", "2026-11-23T10:00:00"),
        ("remind me at half past 6 pm to cook", "cook", "2026-11-20T18:30:00"),
        ("set an alarm for 7 tomorrow morning", "Alarm", "2026-11-21T07:00:00"),
        ("remind me on december 25 at 8 am to call grandma", "call grandma", "2026-12-25T08:00:00"),
    ],
)
def test_reminder_message_and_time(text, message, due):
    r = ents("CREATE_REMINDER", text)
    assert r.entities["operation"] == "create"
    assert r.entities["message"] == message
    assert r.entities["due_at"] == due
    assert not r.missing


def test_reminder_missing_slots():
    r = ents("CREATE_REMINDER", "I need to remember to call my friend tomorrow")
    assert r.entities["message"] == "call my friend"
    assert r.entities["date"] == "2026-11-21"
    assert r.missing == ["time"]
    assert ents("CREATE_REMINDER", "add a reminder to submit my assignment").missing == ["time"]
    assert "message" in ents("CREATE_REMINDER", "set a reminder for 5 pm").missing


def test_reminder_in_the_past_asks_again():
    r = ents("CREATE_REMINDER", "remind me today at 8 am to run")
    assert r.missing == ["time"]
    assert any("passed" in n for n in r.notes)


def test_reminder_operations():
    assert ents("CREATE_REMINDER", "show my reminders").entities["operation"] == "list"
    d = ents("CREATE_REMINDER", "delete the reminder about groceries").entities
    assert d["operation"] == "delete" and d["target"] == "groceries"


@pytest.mark.parametrize(
    "text,operation,operands,value",
    [
        ("Calculate 45 multiplied by 8", "multiplication", [45, 8], 360),
        ("What is 150 divided by 5?", "division", [150, 5], 30),
        ("Add 25 and 37", "addition", [25, 37], 62),
        ("subtract 15 from 40", "subtraction", [40, 15], 25),
        ("Calculate the square of 81", "power", [81, 2], 6561),
        ("what is the square root of 144", "square_root", [144], 12),
        ("what is 15 percent of 200", "percentage", [15, 100, 200], 30),
        ("calculate 2 to the power of 10", "power", [2, 10], 1024),
        ("what is twenty five times four", "multiplication", [25, 4], 100),
        ("evaluate 10 + 20 * 3", "expression", [10, 20, 3], 70),
    ],
)
def test_calculator_extraction_and_evaluation(text, operation, operands, value):
    r = ents("CALCULATE", text)
    assert r.entities["operation"] == operation
    assert r.entities["operands"] == operands
    assert safe_evaluate(r.entities["expression"]) == pytest.approx(value)


def test_calculator_missing_numbers():
    assert ents("CALCULATE", "calculate something").missing == ["expression"]


@pytest.mark.parametrize(
    "expression",
    ["__import__('os').system('dir')", "open('x')", "2 ** 1000000", "(1).__class__", "[1,2]", "a + 1"],
)
def test_safe_evaluator_rejects_code(expression):
    with pytest.raises(CalculationError):
        safe_evaluate(expression)


def test_safe_evaluator_errors():
    with pytest.raises(CalculationError):
        safe_evaluate("5 / 0")
    with pytest.raises(CalculationError):
        safe_evaluate("sqrt(-4)")
    assert build_expression("hello there") is None


@pytest.mark.parametrize(
    "text,key",
    [("open youtube", "youtube"), ("open you tube", "youtube"), ("launch git hub", "github"), ("open githab", "github"),
     ("open my email", "gmail"), ("go to stack overflow", "stackoverflow"), ("open google maps", "maps")],
)
def test_website_extraction(text, key):
    site = find_website(normalize_text(text))
    assert site is not None and site.key == key


def test_website_not_in_allowlist():
    r = ents("OPEN_WEBSITE", "open evil-site.com")
    assert r.missing == ["website"]


