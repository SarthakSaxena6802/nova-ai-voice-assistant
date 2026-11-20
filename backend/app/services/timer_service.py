"""Timers are persisted with an absolute ``ends_at`` so they keep running independently of
the UI (and survive a backend restart). The scheduler completes them."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.timeutils import duration_adjective, humanize_seconds, now
from app.models import Timer
from app.services import notification_service

log = get_logger("timers")

MAX_ACTIVE_TIMERS = 20
MAX_DURATION = 24 * 3600


class TimerError(ValueError):
    pass


def create_timer(db: Session, duration_seconds: int, label: str = "Timer") -> Timer:
    if not 1 <= duration_seconds <= MAX_DURATION:
        raise TimerError("Timers must be between 1 second and 24 hours.")
    if len(active_timers(db)) >= MAX_ACTIVE_TIMERS:
        raise TimerError(f"You already have {MAX_ACTIVE_TIMERS} active timers.")
    start = now()
    timer = Timer(
        label=(label or "Timer")[:120],
        duration_seconds=int(duration_seconds),
        created_at=start,
        ends_at=start + timedelta(seconds=int(duration_seconds)),
        status="active",
    )
    db.add(timer)
    db.commit()
    log.info("Timer #%s created for %ss (%s)", timer.id, duration_seconds, timer.label)
    return timer


def active_timers(db: Session) -> list[Timer]:
    return list(db.scalars(select(Timer).where(Timer.status == "active").order_by(Timer.ends_at)))


def list_timers(db: Session, include_finished: bool = False, limit: int = 50) -> list[Timer]:
    stmt = select(Timer).order_by(Timer.id.desc()).limit(limit)
    if not include_finished:
        stmt = select(Timer).where(Timer.status == "active").order_by(Timer.ends_at)
    return list(db.scalars(stmt))


def get_timer(db: Session, timer_id: int) -> Timer | None:
    return db.get(Timer, timer_id)


def cancel_timer(db: Session, timer: Timer) -> Timer:
    if timer.status != "active":
        raise TimerError("That timer is not running.")
    timer.status = "cancelled"
    timer.finished_at = now()
    db.commit()
    log.info("Timer #%s cancelled", timer.id)
    return timer


def update_duration(db: Session, timer: Timer, duration_seconds: int) -> Timer:
    """Context follow-up ("actually make it 15"): re-base the timer on its original start."""
    if timer.status != "active":
        raise TimerError("That timer has already finished.")
    if not 1 <= duration_seconds <= MAX_DURATION:
        raise TimerError("Timers must be between 1 second and 24 hours.")
    timer.duration_seconds = int(duration_seconds)
    timer.ends_at = timer.created_at + timedelta(seconds=int(duration_seconds))
    if timer.ends_at <= now():
        timer.ends_at = now() + timedelta(seconds=1)
    db.commit()
    return timer


def complete_due(db: Session) -> int:
    due = list(db.scalars(select(Timer).where(Timer.status == "active", Timer.ends_at <= now())))
    for timer in due:
        timer.status = "completed"
        timer.finished_at = now()
        late = (now() - timer.ends_at).total_seconds()
        suffix = " (it finished while Nova was offline)" if late > 30 else ""
        notification_service.create(
            db,
            "timer",
            f"{timer.label} finished",
            f"Your {duration_adjective(timer.duration_seconds)} timer is done{suffix}.",
            timer.id,
        )
        log.info("Timer #%s completed", timer.id)
    if due:
        db.commit()
    return len(due)
