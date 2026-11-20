"""Short-term conversational context.

Deliberately simple (no long-term memory):

* ``pending``      – a question Nova asked and is waiting for (a missing slot such as the
                     reminder time, or a yes/no confirmation of a medium-confidence intent).
* ``last_action``  – the most recent executed action, so follow-ups like
                     "actually make it 15" or "cancel it" can refer to it.

Both expire after ``context_timeout_seconds`` (user setting).
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class PendingAction:
    kind: Literal["slot", "confirm"]
    intent: str
    question: str
    original_text: str
    entities: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    confidence: float = 0.0
    attempts: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class LastAction:
    intent: str
    data: dict[str, Any] = field(default_factory=dict)
    at: float = field(default_factory=time.time)


@dataclass
class ConversationContext:
    session_id: str
    pending: PendingAction | None = None
    last_action: LastAction | None = None
    updated_at: float = field(default_factory=time.time)


class ContextManager:
    MAX_SESSIONS = 200

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationContext] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str, timeout_seconds: float) -> ConversationContext:
        with self._lock:
            ctx = self._sessions.get(session_id)
            if ctx is None:
                if len(self._sessions) >= self.MAX_SESSIONS:
                    oldest = min(self._sessions.values(), key=lambda c: c.updated_at)
                    self._sessions.pop(oldest.session_id, None)
                ctx = ConversationContext(session_id=session_id)
                self._sessions[session_id] = ctx
            now = time.time()
            if ctx.pending and now - ctx.pending.created_at > timeout_seconds:
                ctx.pending = None
            if ctx.last_action and now - ctx.last_action.at > timeout_seconds:
                ctx.last_action = None
            ctx.updated_at = now
            return ctx

    def set_pending(self, ctx: ConversationContext, pending: PendingAction | None) -> None:
        with self._lock:
            ctx.pending = pending

    def set_last_action(self, ctx: ConversationContext, intent: str, data: dict[str, Any]) -> None:
        with self._lock:
            ctx.last_action = LastAction(intent=intent, data=data)

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    @staticmethod
    def snapshot(ctx: ConversationContext) -> dict[str, Any]:
        now = time.time()
        return {
            "pending": {**asdict(ctx.pending), "age_seconds": round(now - ctx.pending.created_at, 1)} if ctx.pending else None,
            "last_action": {**asdict(ctx.last_action), "age_seconds": round(now - ctx.last_action.at, 1)}
            if ctx.last_action
            else None,
        }
