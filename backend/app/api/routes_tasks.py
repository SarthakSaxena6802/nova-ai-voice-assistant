"""Timers, reminders, focus sessions and notifications."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.settings import NovaSettings
from app.schemas.tasks import (
    FocusSessionOut,
    FocusStart,
    FocusStatus,
    NotificationOut,
    ReminderCreate,
    ReminderOut,
    TimerCreate,
    TimerOut,
)
from app.services import focus_service, notification_service, reminder_service, settings_service, timer_service
from app.services.focus_service import FocusError
from app.services.reminder_service import ReminderError
from app.services.timer_service import TimerError

router = APIRouter(prefix="/api")


# ------------------------------------------------------------------- timers
@router.get("/timers", response_model=list[TimerOut], tags=["timers"])
def list_timers(include_finished: bool = False, db: Session = Depends(get_db)) -> list[TimerOut]:
    return [TimerOut.from_orm_timer(t) for t in timer_service.list_timers(db, include_finished)]


@router.post("/timers", response_model=TimerOut, status_code=201, tags=["timers"])
def create_timer(body: TimerCreate, db: Session = Depends(get_db)) -> TimerOut:
    try:
        return TimerOut.from_orm_timer(timer_service.create_timer(db, body.duration_seconds, body.label))
    except TimerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/timers/{timer_id}", response_model=TimerOut, tags=["timers"])
def cancel_timer(timer_id: int, db: Session = Depends(get_db)) -> TimerOut:
    timer = timer_service.get_timer(db, timer_id)
    if timer is None:
        raise HTTPException(status_code=404, detail="Timer not found")
    try:
        return TimerOut.from_orm_timer(timer_service.cancel_timer(db, timer))
    except TimerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------- reminders
@router.get("/reminders", response_model=list[ReminderOut], tags=["reminders"])
def list_reminders(status: Literal["pending", "completed", "all"] = "pending", db: Session = Depends(get_db)) -> list[ReminderOut]:
    return [ReminderOut.from_orm_reminder(r) for r in reminder_service.list_reminders(db, status)]


@router.post("/reminders", response_model=ReminderOut, status_code=201, tags=["reminders"])
def create_reminder(body: ReminderCreate, db: Session = Depends(get_db)) -> ReminderOut:
    try:
        return ReminderOut.from_orm_reminder(reminder_service.create_reminder(db, body.message, body.due_at))
    except ReminderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/reminders/{reminder_id}/complete", response_model=ReminderOut, tags=["reminders"])
def complete_reminder(reminder_id: int, db: Session = Depends(get_db)) -> ReminderOut:
    reminder = reminder_service.get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return ReminderOut.from_orm_reminder(reminder_service.complete_reminder(db, reminder))


@router.delete("/reminders/{reminder_id}", tags=["reminders"])
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    reminder = reminder_service.get_reminder(db, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder_service.delete_reminder(db, reminder)
    return {"ok": True}


@router.delete("/reminders", tags=["reminders"])
def clear_reminders(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"deleted": reminder_service.clear_reminders(db)}


# -------------------------------------------------------------------- focus
@router.get("/focus", response_model=FocusStatus, tags=["focus"])
def focus_status(db: Session = Depends(get_db)) -> FocusStatus:
    return focus_service.status(db)


@router.post("/focus/start", response_model=FocusSessionOut, status_code=201, tags=["focus"])
def focus_start(body: FocusStart | None = None, db: Session = Depends(get_db)) -> FocusSessionOut:
    prefs: NovaSettings = settings_service.get_settings(db)
    minutes = (body.duration_minutes if body and body.duration_minutes else None) or prefs.focus_default_minutes
    try:
        return focus_service.to_out(focus_service.start_session(db, minutes * 60))  # type: ignore[return-value]
    except FocusError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/focus/stop", response_model=FocusSessionOut, tags=["focus"])
def focus_stop(db: Session = Depends(get_db)) -> FocusSessionOut:
    session = focus_service.stop_session(db)
    if session is None:
        raise HTTPException(status_code=409, detail="No focus session is running")
    return focus_service.to_out(session)  # type: ignore[return-value]


# ------------------------------------------------------------ notifications
@router.get("/notifications", response_model=list[NotificationOut], tags=["notifications"])
def notifications(unread_only: bool = True, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)) -> list[NotificationOut]:
    return [NotificationOut.model_validate(n) for n in notification_service.list_notifications(db, unread_only, limit)]


@router.post("/notifications/{notification_id}/read", tags=["notifications"])
def mark_read(notification_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    return {"updated": notification_service.mark_read(db, notification_id)}


@router.post("/notifications/read-all", tags=["notifications"])
def mark_all_read(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"updated": notification_service.mark_read(db)}
