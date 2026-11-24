from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.timeutils import now


class TimerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    duration_seconds: int
    created_at: datetime
    ends_at: datetime
    status: str
    finished_at: datetime | None = None
    remaining_seconds: int = 0

    @classmethod
    def from_orm_timer(cls, timer) -> "TimerOut":
        out = cls.model_validate(timer)
        out.remaining_seconds = max(0, int((timer.ends_at - now()).total_seconds())) if timer.status == "active" else 0
        return out


class TimerCreate(BaseModel):
    duration_seconds: int = Field(..., ge=1, le=24 * 3600)
    label: str = Field("Timer", max_length=120)


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    due_at: datetime
    created_at: datetime
    status: str
    notified: bool
    completed_at: datetime | None = None
    overdue: bool = False

    @classmethod
    def from_orm_reminder(cls, reminder) -> "ReminderOut":
        out = cls.model_validate(reminder)
        out.overdue = reminder.status == "pending" and reminder.due_at <= now()
        return out


class ReminderCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=300)
    due_at: datetime

    @field_validator("message")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        return v

    @field_validator("due_at")
    @classmethod
    def _future(cls, v: datetime) -> datetime:
        v = v.replace(tzinfo=None) if v.tzinfo is None else v.astimezone().replace(tzinfo=None)
        if v <= now():
            raise ValueError("due_at must be in the future")
        return v


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    kind: str
    title: str
    message: str
    ref_id: int | None = None
    read: bool
