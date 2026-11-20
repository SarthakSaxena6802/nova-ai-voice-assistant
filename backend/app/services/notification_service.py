from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import Notification


def create(db: Session, kind: str, title: str, message: str, ref_id: int | None = None) -> Notification:
    note = Notification(kind=kind, title=title, message=message, ref_id=ref_id)
    db.add(note)
    db.flush()
    return note


def list_notifications(db: Session, unread_only: bool = True, limit: int = 50) -> list[Notification]:
    stmt = select(Notification).order_by(Notification.id.desc()).limit(limit)
    if unread_only:
        stmt = stmt.where(Notification.read.is_(False))
    return list(db.scalars(stmt))


def mark_read(db: Session, notification_id: int | None = None) -> int:
    stmt = update(Notification).values(read=True)
    if notification_id is not None:
        stmt = stmt.where(Notification.id == notification_id)
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0
