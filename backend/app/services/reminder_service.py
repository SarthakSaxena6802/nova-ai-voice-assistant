"""Reminders persist in SQLite; the scheduler raises a notification when they fall due."""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.timeutils import now
from app.models import Reminder
from app.services import notification_service

log = get_logger("reminders")


class ReminderError(ValueError):
    pass


def create_reminder(db: Session, message: str, due_at: datetime) -> Reminder:
    message = (message or "").strip()
    if not message:
        raise ReminderError("A reminder needs a message.")
    if len(message) > 300:
        raise ReminderError("That reminder message is too long.")
    if due_at <= now():
        raise ReminderError("That time has already passed.")
    reminder = Reminder(message=message, due_at=due_at.replace(microsecond=0), status="pending")
    db.add(reminder)
    db.commit()
    log.info("Reminder #%s created for %s", reminder.id, reminder.due_at.isoformat())
    return reminder


def list_reminders(db: Session, status: str | None = "pending") -> list[Reminder]:
    stmt = select(Reminder).order_by(Reminder.due_at)
    if status and status != "all":
        stmt = stmt.where(Reminder.status == status)
    return list(db.scalars(stmt))


def get_reminder(db: Session, reminder_id: int) -> Reminder | None:
    return db.get(Reminder, reminder_id)


def complete_reminder(db: Session, reminder: Reminder) -> Reminder:
    reminder.status = "completed"
    reminder.completed_at = now()
    db.commit()
    return reminder


def reschedule(db: Session, reminder: Reminder, due_at: datetime) -> Reminder:
    if due_at <= now():
        raise ReminderError("That time has already passed.")
    reminder.due_at = due_at
    reminder.notified = False
    db.commit()
    return reminder


def delete_reminder(db: Session, reminder: Reminder) -> None:
    db.delete(reminder)
    db.commit()


def clear_reminders(db: Session) -> int:
    result = db.execute(delete(Reminder))
    db.commit()
    return result.rowcount or 0


def find_best_match(db: Session, words: str) -> Reminder | None:
    """Pick the pending reminder whose message shares the most words with *words*."""
    pending = list_reminders(db, "pending")
    if not pending:
        return None
    query = {w for w in re.findall(r"[a-z0-9]+", words.lower()) if len(w) > 2 and w not in {"the", "about", "for", "reminder", "my"}}
    if not query:
        return pending[0] if len(pending) == 1 else None
    scored = [(len(query & set(re.findall(r"[a-z0-9]+", r.message.lower()))), r) for r in pending]
    best_score, best = max(scored, key=lambda s: s[0])
    return best if best_score > 0 else None


def notify_due(db: Session) -> int:
    due = list(
        db.scalars(
            select(Reminder).where(Reminder.status == "pending", Reminder.notified.is_(False), Reminder.due_at <= now())
        )
    )
    for reminder in due:
        reminder.notified = True
        notification_service.create(db, "reminder", "Reminder", reminder.message[0].upper() + reminder.message[1:], reminder.id)
        log.info("Reminder #%s is due", reminder.id)
    if due:
        db.commit()
    return len(due)
