"""Focus (productivity) sessions: a single active countdown + completed-session statistics."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.timeutils import humanize_seconds, now
from app.models import FocusSession
from app.schemas.tasks import FocusSessionOut, FocusStatus
from app.services import notification_service

log = get_logger("focus")


class FocusError(ValueError):
    pass


def active_session(db: Session) -> FocusSession | None:
    return db.scalars(select(FocusSession).where(FocusSession.status == "active").limit(1)).first()


def start_session(db: Session, duration_seconds: int) -> FocusSession:
    if not 60 <= duration_seconds <= 4 * 3600:
        raise FocusError("Focus sessions can be between 1 minute and 4 hours.")
    if active_session(db):
        raise FocusError("A focus session is already running.")
    start = now()
    session = FocusSession(duration_seconds=duration_seconds, started_at=start, ends_at=start + timedelta(seconds=duration_seconds))
    db.add(session)
    db.commit()
    log.info("Focus session #%s started (%ss)", session.id, duration_seconds)
    return session


def update_duration(db: Session, session: FocusSession, duration_seconds: int) -> FocusSession:
    if not 60 <= duration_seconds <= 4 * 3600:
        raise FocusError("Focus sessions can be between 1 minute and 4 hours.")
    session.duration_seconds = duration_seconds
    session.ends_at = session.started_at + timedelta(seconds=duration_seconds)
    if session.ends_at <= now():
        session.ends_at = now() + timedelta(seconds=1)
    db.commit()
    return session


def stop_session(db: Session) -> FocusSession | None:
    session = active_session(db)
    if session is None:
        return None
    session.status = "stopped"
    session.ended_at = now()
    db.commit()
    log.info("Focus session #%s stopped early", session.id)
    return session


def complete_due(db: Session) -> int:
    due = list(db.scalars(select(FocusSession).where(FocusSession.status == "active", FocusSession.ends_at <= now())))
    for session in due:
        session.status = "completed"
        session.ended_at = now()
        notification_service.create(
            db,
            "focus",
            "Focus session complete",
            f"Great work! You stayed focused for {humanize_seconds(session.duration_seconds)}. Time for a short break.",
            session.id,
        )
    if due:
        db.commit()
    return len(due)


def to_out(session: FocusSession | None) -> FocusSessionOut | None:
    if session is None:
        return None
    out = FocusSessionOut.model_validate(session)
    out.remaining_seconds = max(0, int((session.ends_at - now()).total_seconds())) if session.status == "active" else 0
    return out


def status(db: Session) -> FocusStatus:
    completed = select(FocusSession).where(FocusSession.status == "completed")
    count = db.scalar(select(func.count()).select_from(completed.subquery())) or 0
    start_of_day = now().replace(hour=0, minute=0, second=0)
    today = db.scalar(
        select(func.count()).select_from(completed.where(FocusSession.ended_at >= start_of_day).subquery())
    ) or 0
    total = db.scalar(select(func.coalesce(func.sum(FocusSession.duration_seconds), 0)).where(FocusSession.status == "completed")) or 0
    return FocusStatus(active=to_out(active_session(db)), completed_sessions=count, completed_today=today, total_focus_minutes=int(total) // 60)
