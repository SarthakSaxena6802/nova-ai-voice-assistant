"""Background loop that completes timers / focus sessions and fires due reminders.

Runs inside the backend process, so timers keep working whether or not a browser tab is
open. The UI learns about completions by polling ``/api/notifications``.
"""
from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.database.session import session_scope
from app.services import focus_service, reminder_service, timer_service

log = get_logger("scheduler")


def tick() -> int:
    with session_scope() as db:
        return timer_service.complete_due(db) + reminder_service.notify_due(db) + focus_service.complete_due(db)


async def run_scheduler(interval: float, stop: asyncio.Event) -> None:
    log.info("Scheduler started (every %.1fs)", interval)
    while not stop.is_set():
        try:
            await asyncio.to_thread(tick)
        except Exception:
            log.exception("Scheduler tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    log.info("Scheduler stopped")
