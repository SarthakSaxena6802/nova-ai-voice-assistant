"""Offline actions: greeting, time, date, calculator."""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from app.actions.base import ActionContext, ActionResult, BaseAction
from app.core.timeutils import format_date, format_time
from app.nlp.math_expression import CalculationError, format_number, safe_evaluate


class GreetingAction(BaseAction):
    intent = "GREETING"
    name = "Greetings"
    description = "Small talk and greetings."
    examples = ["Hello Nova", "Good morning", "How are you?"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        hour = ctx.now.hour
        part = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        name = f", {ctx.prefs.user_name}" if ctx.prefs.user_name else ""
        if re.search(r"\bhow are you|how is it going|how have you been|how is your day|how do you do\b", ctx.text):
            msg = f"I'm doing great, thanks for asking{name}! What can I do for you?"
        elif re.search(r"\bgood night\b", ctx.text):
            msg = f"Good night{name}! Sleep well."
        else:
            msg = f"Good {part}{name}! I'm {ctx.prefs.assistant_name}. How can I help you?"
        return self.ok(msg)


class TimeAction(BaseAction):
    intent = "GET_TIME"
    name = "Time"
    description = "Tells the current local time. Works offline."
    examples = ["What time is it?", "Tell me the current time"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        return self.ok(f"It's {format_time(ctx.now)}.", {"time": ctx.now.strftime("%H:%M:%S"), "iso": ctx.now.isoformat()})


class DateAction(BaseAction):
    intent = "GET_DATE"
    name = "Date"
    description = "Tells today's date, day of the week, month or year. Works offline."
    examples = ["What is today's date?", "What day is it?", "What day is it tomorrow?"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        offset = int(entities.get("offset_days", 0))
        day = ctx.now + timedelta(days=offset)
        label = {0: "Today", 1: "Tomorrow", 2: "The day after tomorrow", -1: "Yesterday"}.get(offset, "That day")
        verb = "was" if offset < 0 else "will be" if offset > 0 else "is"
        focus = entities.get("focus", "date")
        if focus == "month" and offset == 0:
            msg = f"It's {day.strftime('%B')} {day.year}."
        elif focus == "year" and offset == 0:
            msg = f"It's {day.year}."
        elif focus == "weekday" and "weekend" in ctx.text and offset == 0:
            is_weekend = day.weekday() >= 5
            msg = f"{'Yes' if is_weekend else 'Not yet'}, today is {day.strftime('%A')}."
        else:
            msg = f"{label} {verb} {format_date(day)}."
        return self.ok(msg, {"date": day.date().isoformat(), "weekday": day.strftime("%A")})


_SPOKEN_OPS = [("sqrt", "the square root of "), ("cbrt", "the cube root of "), ("*", " times "), ("/", " divided by "),
               ("^", " to the power of "), ("+", " plus "), ("%", " modulo ")]


def _spoken(expression: str) -> str:
    text = expression
    for sym, word in _SPOKEN_OPS:
        text = text.replace(sym, word)
    text = re.sub(r"(?<=\d) - (?=\d)", " minus ", text)
    text = re.sub(r"[()]", "", text)
    return re.sub(r"\s+", " ", text).strip()


class CalculatorAction(BaseAction):
    intent = "CALCULATE"
    name = "Calculator"
    description = "Safe arithmetic: + − × ÷, percentages, powers, square and cube roots (no eval)."
    examples = ["Calculate 45 multiplied by 8", "What is 15 percent of 200?", "Square root of 144"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        expression = entities.get("expression")
        if not expression:
            return self.fail("I didn't catch the numbers to calculate.", "missing_expression")
        try:
            value = safe_evaluate(expression)
        except CalculationError as exc:
            return self.fail(str(exc), "calculation_error", {"expression": expression})
        result = format_number(value)
        operands = entities.get("operands", [])
        if entities.get("operation") == "percentage" and len(operands) >= 3 and "/ 100 *" in expression.replace("(", ""):
            spoken = f"{format_number(operands[0])} percent of {format_number(operands[-1])}"
        else:
            spoken = _spoken(expression)
        return self.ok(
            f"{spoken[0].upper() + spoken[1:]} is {result}.",
            {"expression": expression, "result": value, "formatted": result},
        )
