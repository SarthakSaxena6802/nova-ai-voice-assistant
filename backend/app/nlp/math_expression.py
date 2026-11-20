"""Natural-language arithmetic → safe expression → value.

No ``eval``: the expression is parsed with Python's ``ast`` module and evaluated by a
tiny interpreter that only knows numbers, + - * / % ** and sqrt/cbrt/abs.
"""
from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass, field

NUM = r"(-?\d+(?:\.\d+)?)"

# (pattern, replacement) applied in order on normalised text
_PHRASES: list[tuple[str, str]] = [
    (rf"\bsquare\s+root\s+of\s+{NUM}", r" sqrt(\1) "),
    (rf"\bcube\s+root\s+of\s+{NUM}", r" cbrt(\1) "),
    (rf"\b(?:the\s+)?square\s+of\s+{NUM}", r" (\1)^2 "),
    (rf"\b(?:the\s+)?cube\s+of\s+{NUM}", r" (\1)^3 "),
    (rf"{NUM}\s+squared\b", r" (\1)^2 "),
    (rf"{NUM}\s+cubed\b", r" (\1)^3 "),
    (rf"{NUM}\s*(?:percent|%)\s+(?:tip\s+)?(?:of|on)\s+{NUM}", r" (\1/100*\2) "),
    (rf"{NUM}\s+(?:to\s+the\s+power\s+of|raised\s+to(?:\s+the\s+power\s+of)?|to\s+the|power)\s+half\b", r" (\1)^0.5 "),
    (rf"{NUM}\s+(?:to\s+the\s+power\s+of|raised\s+to(?:\s+the\s+power\s+of)?|to\s+the|power)\s+{NUM}", r" (\1)^(\2) "),
    (rf"\b(?:add|sum\s+of|sum|plus|total\s+of)\s+{NUM}\s+(?:and|to|with|plus)\s+{NUM}", r" (\1+\2) "),
    (rf"\bsubtract\s+{NUM}\s+from\s+{NUM}", r" (\2-\1) "),
    (rf"\b(?:the\s+)?difference\s+(?:between|of)\s+{NUM}\s+and\s+{NUM}", r" (\1-\2) "),
    (rf"\bmultiply\s+{NUM}\s+(?:by|and|with|times)\s+{NUM}", r" (\1*\2) "),
    (rf"\b(?:the\s+)?product\s+of\s+{NUM}\s+and\s+{NUM}", r" (\1*\2) "),
    (rf"\bdivide\s+{NUM}\s+(?:by|over)\s+{NUM}", r" (\1/\2) "),
    (rf"\b(?:the\s+)?quotient\s+of\s+{NUM}\s+and\s+{NUM}", r" (\1/\2) "),
    (rf"{NUM}\s+(?:percent|%)", r" (\1/100) "),
    (r"\b(?:multiplied\s+by|multiply\s+by|multiply|times|into|x)\b", " * "),
    (r"\b(?:divided\s+by|divide\s+by|over)\b", " / "),
    (r"\b(?:plus|and)\b", " + "),
    (r"\bminus\b", " - "),
    (r"\b(?:mod|modulo)\b", " % "),
]
_ALLOWED_TOKEN = re.compile(r"\d+(?:\.\d+)?|sqrt|cbrt|abs|[()+\-*/^%]")

_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"sqrt": math.sqrt, "cbrt": lambda v: math.copysign(abs(v) ** (1 / 3), v), "abs": abs}

OP_NAMES = {
    "+": "addition", "-": "subtraction", "*": "multiplication", "/": "division",
    "^": "power", "%": "modulo", "sqrt": "square_root", "cbrt": "cube_root",
}


class CalculationError(ValueError):
    pass


@dataclass
class MathExpression:
    expression: str  # human-readable, e.g. "45 * 8"
    operation: str
    operands: list[float] = field(default_factory=list)


def build_expression(text: str) -> MathExpression | None:
    """Translate normalised text into an arithmetic expression. Returns None if no numbers."""
    work = f" {text} "
    percent_used = bool(re.search(r"\bpercent\b|%", work))
    for pattern, repl in _PHRASES:
        work = re.sub(pattern, repl, work)
    tokens = _ALLOWED_TOKEN.findall(work)
    # drop leading/trailing binary operators produced by filler words like "and"
    while tokens and tokens[0] in "+*/^%":
        tokens.pop(0)
    while tokens and tokens[-1] in "+-*/^%":
        tokens.pop()
    numbers = [float(t) for t in tokens if re.fullmatch(r"\d+(?:\.\d+)?", t)]
    if not numbers:
        return None
    expression = " ".join(tokens).replace("( ", "(").replace(" )", ")")
    ops = [OP_NAMES[t] for t in tokens if t in OP_NAMES]
    distinct = list(dict.fromkeys(ops))
    if percent_used:
        operation = "percentage"
    elif len(distinct) == 1:
        operation = distinct[0]
    elif not distinct:
        operation = "value"
    else:
        operation = "expression"
    return MathExpression(expression=expression, operation=operation, operands=numbers)


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > 100 or (abs(left) > 1e6 and right > 3):
                raise CalculationError("That exponent is too large for me to compute.")
            if left < 0 and not float(right).is_integer():
                raise CalculationError("I can't raise a negative number to a fractional power.")
        if isinstance(node.op, (ast.Div, ast.Mod)) and right == 0:
            raise CalculationError("You can't divide by zero.")
        return float(_BIN_OPS[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return float(_UNARY[type(node.op)](_eval(node.operand)))
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCS
        and len(node.args) == 1
        and not node.keywords
    ):
        arg = _eval(node.args[0])
        if node.func.id == "sqrt" and arg < 0:
            raise CalculationError("The square root of a negative number isn't a real number.")
        return float(_FUNCS[node.func.id](arg))
    raise CalculationError("That expression contains something I can't calculate.")


def safe_evaluate(expression: str) -> float:
    if len(expression) > 200:
        raise CalculationError("That expression is too long.")
    try:
        tree = ast.parse(expression.replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise CalculationError("I couldn't understand that calculation.") from exc
    value = _eval(tree)
    if math.isnan(value) or math.isinf(value) or abs(value) > 1e15:
        raise CalculationError("The result is too large to compute.")
    return value


def format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}"
    text = f"{value:,.6f}".rstrip("0").rstrip(".")
    return text
