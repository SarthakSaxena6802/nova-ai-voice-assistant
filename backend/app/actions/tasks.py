"""Stateful actions: timers, reminders, focus sessions."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.actions.base import ActionContext, ActionResult, BaseAction, second_person
from app.core.timeutils import describe_datetime, duration_adjective, humanize_seconds
from app.schemas.tasks import ReminderOut, TimerOut
from app.services import focus_service, reminder_service, timer_service
from app.services.focus_service import FocusError
from app.services.reminder_service import ReminderError
from app.services.timer_service import TimerError


class TimerAction(BaseAction):
    intent = "SET_TIMER"
    name = "Timers"
    description = "Create, check and cancel countdown timers. Multiple timers can run at once; they keep running in the backend."
    examples = ["Set a timer for 10 minutes", "Start a 5-minute countdown", "How much time is left?", "Cancel my timer"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        op = entities.get("operation", "create")
        if op == "cancel":
            return self._cancel(entities, ctx)
        if op == "status":
            return self._status(ctx)
        seconds = entities.get("duration_seconds")
        if not seconds:
            return self.fail("How long should the timer be?", "missing_duration")
        label = entities.get("label") or "Timer"
        try:
            timer = timer_service.create_timer(ctx.db, int(seconds), label)
        except TimerError as exc:
            return self.fail(str(exc), "invalid_timer")
        named = f" {label.lower()}" if label != "Timer" else ""
        return self.ok(
            f"Your{named} timer is set for {humanize_seconds(timer.duration_seconds)}.",
            {"timer": TimerOut.from_orm_timer(timer).model_dump(mode="json"), "duration_seconds": timer.duration_seconds},
            context={"timer_id": timer.id, "duration_seconds": timer.duration_seconds},
        )

    def _cancel(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        active = timer_service.active_timers(ctx.db)
        if not active:
            return self.fail("You don't have any timers running.", "no_active_timers")
        if entities.get("scope") == "all":
            for t in active:
                timer_service.cancel_timer(ctx.db, t)
            return self.ok(f"Cancelled all {len(active)} timer{'s' if len(active) > 1 else ''}.", {"cancelled": [t.id for t in active]})
        target = None
        if ctx.last_action and ctx.last_action.get("timer_id"):
            target = next((t for t in active if t.id == ctx.last_action["timer_id"]), None)
        target = target or max(active, key=lambda t: t.created_at)
        timer_service.cancel_timer(ctx.db, target)
        return self.ok(f"Cancelled your {duration_adjective(target.duration_seconds)} timer.", {"cancelled": [target.id]})

    def _status(self, ctx: ActionContext) -> ActionResult:
        active = timer_service.active_timers(ctx.db)
        if not active:
            return self.ok("You don't have any timers running.", {"timers": []})
        outs = [TimerOut.from_orm_timer(t) for t in active]
        parts = [f"{humanize_seconds(o.remaining_seconds)} left on your {o.label.lower() if o.label != 'Timer' else duration_adjective(o.duration_seconds)} timer" for o in outs[:3]]
        msg = ("There's " if len(parts) == 1 else "You have: ") + "; ".join(parts) + "."
        return self.ok(msg, {"timers": [o.model_dump(mode="json") for o in outs]})


class ReminderAction(BaseAction):
    intent = "CREATE_REMINDER"
    name = "Reminders"
    description = "Create, list, complete and delete reminders. Stored in SQLite, so they survive restarts."
    examples = ["Remind me to study at 8 PM", "Remind me tomorrow at 9 AM to attend my meeting", "Show my reminders"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        op = entities.get("operation", "create")
        if op == "list":
            return self._list(ctx)
        if op in ("complete", "delete"):
            return self._modify(op, entities, ctx)
        message, due = entities.get("message"), entities.get("due_at")
        if not message or not due:
            return self.fail("I need both what to remind you about and when.", "missing_parameters")
        try:
            reminder = reminder_service.create_reminder(ctx.db, message, datetime.fromisoformat(due))
        except (ReminderError, ValueError) as exc:
            return self.fail(str(exc), "invalid_reminder")
        when = describe_datetime(reminder.due_at, ctx.now)
        if message.lower() == "alarm":
            text = f"Your alarm is set for {when}."
        else:
            spoken = second_person(message)
            joiner = "about" if re.match(r"^(your|the|a|an|our)\b", spoken) else "to"
            text = f"Okay, I'll remind you {joiner} {spoken} {when}."
        return self.ok(
            text,
            {"reminder": ReminderOut.from_orm_reminder(reminder).model_dump(mode="json")},
            context={"reminder_id": reminder.id},
        )

    def _list(self, ctx: ActionContext) -> ActionResult:
        pending = reminder_service.list_reminders(ctx.db, "pending")
        if not pending:
            return self.ok("You don't have any pending reminders.", {"reminders": []})
        items = [f"{second_person(r.message)} {describe_datetime(r.due_at, ctx.now)}" for r in pending[:5]]
        more = f" and {len(pending) - 5} more" if len(pending) > 5 else ""
        msg = f"You have {len(pending)} pending reminder{'s' if len(pending) > 1 else ''}: " + "; ".join(items) + more + "."
        return self.ok(msg, {"reminders": [ReminderOut.from_orm_reminder(r).model_dump(mode="json") for r in pending]})

    def _modify(self, op: str, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        if op == "delete" and entities.get("scope") == "all":
            pending = reminder_service.list_reminders(ctx.db, "pending")
            for r in pending:
                reminder_service.delete_reminder(ctx.db, r)
            return self.ok(f"Deleted {len(pending)} reminder{'s' if len(pending) != 1 else ''}.")
        target = None
        if entities.get("target"):
            target = reminder_service.find_best_match(ctx.db, entities["target"])
        if target is None and ctx.last_action and ctx.last_action.get("reminder_id"):
            target = reminder_service.get_reminder(ctx.db, ctx.last_action["reminder_id"])
        if target is None:
            pending = reminder_service.list_reminders(ctx.db, "pending")
            if len(pending) == 1:
                target = pending[0]
            elif not pending:
                return self.fail("You don't have any pending reminders.", "no_reminders")
            else:
                return self.fail(
                    "Which reminder do you mean? You can say something like 'delete the reminder about groceries', "
                    "or manage them on the dashboard.",
                    "ambiguous_reminder",
                )
        if op == "complete":
            reminder_service.complete_reminder(ctx.db, target)
            return self.ok(f"Marked '{second_person(target.message)}' as done.", {"reminder_id": target.id})
        reminder_service.delete_reminder(ctx.db, target)
        return self.ok(f"Deleted the reminder to {second_person(target.message)}.", {"reminder_id": target.id})


class FocusAction(BaseAction):
    intent = "FOCUS_MODE"
    name = "Focus mode"
    description = "Pomodoro-style focus sessions with a countdown, completion notification and session statistics."
    examples = ["Enable focus mode", "Start a 50 minute focus session", "Stop focus mode"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        op = entities.get("operation", "start")
        if op == "stop":
            session = focus_service.stop_session(ctx.db)
            if session is None:
                return self.fail("Focus mode isn't on right now.", "no_active_session")
            return self.ok("Focus mode is off. Nice work!", {"focus": focus_service.to_out(session).model_dump(mode="json")})
        if op == "status":
            session = focus_service.active_session(ctx.db)
            if session is None:
                return self.ok("Focus mode is off.", {"focus": None})
            out = focus_service.to_out(session)
            return self.ok(f"You're in focus mode with {humanize_seconds(out.remaining_seconds)} remaining.", {"focus": out.model_dump(mode="json")})
        seconds = int(entities.get("duration_seconds") or ctx.prefs.focus_default_minutes * 60)
        try:
            session = focus_service.start_session(ctx.db, seconds)
        except FocusError as exc:
            return self.fail(str(exc), "focus_error")
        return self.ok(
            f"Focus mode is on for {humanize_seconds(seconds)}. I'll let you know when it's time for a break.",
            {"focus": focus_service.to_out(session).model_dump(mode="json")},
            context={"focus_id": session.id, "duration_seconds": seconds},
        )
