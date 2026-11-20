"""Context manager, logging redaction and time helpers."""
from __future__ import annotations

import logging
import time

from app.context.manager import ContextManager, PendingAction
from app.core.logging import RedactingFilter, redact
from app.core.timeutils import humanize_seconds


def test_context_expires():
    cm = ContextManager()
    ctx = cm.get("s1", timeout_seconds=60)
    cm.set_pending(ctx, PendingAction(kind="slot", intent="SET_TIMER", question="?", original_text="set a timer"))
    cm.set_last_action(ctx, "SET_TIMER", {"timer_id": 1})
    assert cm.get("s1", 60).pending is not None
    ctx.pending.created_at = time.time() - 120
    ctx.last_action.at = time.time() - 120
    fresh = cm.get("s1", 60)
    assert fresh.pending is None and fresh.last_action is None


def test_context_sessions_are_isolated():
    cm = ContextManager()
    a = cm.get("a", 60)
    cm.set_last_action(a, "SET_TIMER", {"timer_id": 1})
    assert cm.get("b", 60).last_action is None
    cm.reset("a")
    assert cm.get("a", 60).last_action is None


def test_secrets_are_redacted():
    assert "sk-ant-abc" not in redact("key is sk-ant-abc123456789xyz")
    assert redact("api_key=supersecret") == "api_key=[REDACTED]"
    assert "tok" not in redact("Authorization: Bearer tok.en.value")
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "using %s", ("sk-ant-0123456789abcdef",), None)
    RedactingFilter().filter(record)
    assert "0123456789" not in record.getMessage()


def test_humanize_seconds():
    assert humanize_seconds(300) == "5 minutes"
    assert humanize_seconds(5400) == "1 hour and 30 minutes"
    assert humanize_seconds(3661) == "1 hour, 1 minute and 1 second"
