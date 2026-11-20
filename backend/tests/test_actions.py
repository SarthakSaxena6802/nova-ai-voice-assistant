"""Action handlers and services, tested independently of the HTTP layer."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.actions.base import ActionContext, second_person
from app.actions.registry import build_default_registry
from app.core.timeutils import now
from app.models import Timer
from app.nlp.websites import SAFE_WEBSITES
from app.schemas.settings import NovaSettings
from app.services import focus_service, notification_service, reminder_service, timer_service
from app.services.knowledge_base import KnowledgeBase


@pytest.fixture()
def registry():
    return build_default_registry()


@pytest.fixture()
def actx(db, settings):
    kb = KnowledgeBase()
    kb.load(settings.knowledge_base_path)
    return ActionContext(db=db, prefs=NovaSettings(), now=datetime(2026, 11, 20, 19, 5), text="", knowledge_base=kb)


def test_time_service(registry, actx):
    r = registry.execute("GET_TIME", {}, actx)
    assert r.success and r.message == "It's 7:05 PM."


def test_date_service(registry, actx):
    r = registry.execute("GET_DATE", {}, actx)
    assert r.success and r.message == "Today is Friday, November 20, 2026."
    r = registry.execute("GET_DATE", {"offset_days": 1}, actx)
    assert "Saturday, November 21, 2026" in r.message


def test_calculator_action(registry, actx):
    r = registry.execute("CALCULATE", {"expression": "45 * 8", "operation": "multiplication", "operands": [45, 8]}, actx)
    assert r.success and r.message == "45 times 8 is 360." and r.data["result"] == 360
    r = registry.execute("CALCULATE", {"expression": "(5 / 0)"}, actx)
    assert not r.success and r.error == "calculation_error"


def test_timer_creation_status_and_cancel(registry, actx, db):
    r = registry.execute("SET_TIMER", {"operation": "create", "duration_seconds": 300}, actx)
    assert r.success and r.message == "Your timer is set for 5 minutes."
    timer_id = r.data["timer"]["id"]
    assert r.context == {"timer_id": timer_id, "duration_seconds": 300}
    assert any(t.id == timer_id for t in timer_service.active_timers(db))

    status = registry.execute("SET_TIMER", {"operation": "status"}, actx)
    assert status.success and "left on your 5-minute timer" in status.message

    actx.last_action = {"timer_id": timer_id}
    cancel = registry.execute("SET_TIMER", {"operation": "cancel", "scope": "latest"}, actx)
    assert cancel.success and timer_id in cancel.data["cancelled"]


def test_timer_validation(registry, actx):
    r = registry.execute("SET_TIMER", {"operation": "create", "duration_seconds": 999999}, actx)
    assert not r.success and r.error == "invalid_timer"


def test_timer_completion_creates_notification(db):
    t = Timer(label="Tea", duration_seconds=60, created_at=now() - timedelta(seconds=61), ends_at=now() - timedelta(seconds=1))
    db.add(t)
    db.commit()
    assert timer_service.complete_due(db) >= 1
    db.refresh(t)
    assert t.status == "completed"
    notes = notification_service.list_notifications(db)
    assert any(n.kind == "timer" and n.ref_id == t.id for n in notes)


def test_reminder_creation_and_persistence(registry, actx, db):
    due = (now() + timedelta(days=1)).replace(hour=20, minute=0, second=0)
    r = registry.execute("CREATE_REMINDER", {"operation": "create", "message": "call my friend", "due_at": due.isoformat()}, actx)
    assert r.success and "remind you to call your friend" in r.message
    rid = r.data["reminder"]["id"]
    stored = reminder_service.get_reminder(db, rid)
    assert stored is not None and stored.status == "pending" and stored.due_at == due

    listed = registry.execute("CREATE_REMINDER", {"operation": "list"}, actx)
    assert listed.success and any(x["id"] == rid for x in listed.data["reminders"])

    done = registry.execute("CREATE_REMINDER", {"operation": "complete", "target": "friend"}, actx)
    assert done.success
    assert reminder_service.get_reminder(db, rid).status == "completed"


def test_reminder_rejects_past_time(registry, actx):
    past = (now() - timedelta(hours=1)).isoformat()
    r = registry.execute("CREATE_REMINDER", {"operation": "create", "message": "x", "due_at": past}, actx)
    assert not r.success and r.error == "invalid_reminder"


def test_due_reminder_notifies_once(db):
    rem = reminder_service.create_reminder(db, "drink water", now() + timedelta(seconds=1))
    rem.due_at = now() - timedelta(seconds=1)
    db.commit()
    assert reminder_service.notify_due(db) >= 1
    assert reminder_service.notify_due(db) == 0  # not twice
    db.refresh(rem)
    assert rem.notified and rem.status == "pending"


def test_focus_mode(registry, actx, db):
    focus_service.stop_session(db)
    r = registry.execute("FOCUS_MODE", {"operation": "start", "duration_seconds": 1500}, actx)
    assert r.success and "25 minutes" in r.message
    again = registry.execute("FOCUS_MODE", {"operation": "start"}, actx)
    assert not again.success  # only one session at a time
    stop = registry.execute("FOCUS_MODE", {"operation": "stop"}, actx)
    assert stop.success and focus_service.active_session(db) is None


def test_website_mapping_uses_allowlist(registry, actx):
    r = registry.execute("OPEN_WEBSITE", {"website": "YouTube", "url": "https://www.youtube.com"}, actx)
    assert r.success and r.data["url"] == SAFE_WEBSITES["youtube"].url and r.data["opened_by"] == "client"
    bad = registry.execute("OPEN_WEBSITE", {"website": "Evil", "url": "https://evil.example.com"}, actx)
    assert not bad.success and bad.error == "not_allowed"


def test_weather_disabled_does_not_fabricate(registry, actx):
    r = registry.execute("WEATHER_QUERY", {"city": "London", "day": "today"}, actx)
    assert not r.success and r.error == "weather_not_configured"
    assert "°" not in r.message


def test_question_uses_knowledge_base_offline(registry, actx):
    r = registry.execute("ASK_QUESTION", {"question": "explain machine learning"}, actx)
    assert r.success and r.data["source"] == "knowledge_base"
    unknown = registry.execute("ASK_QUESTION", {"question": "who won the football match yesterday"}, actx)
    assert not unknown.success and unknown.error == "no_answer"


def test_registry_contains_handler_crashes(registry, actx):
    class Boom:
        intent = "BOOM"

        def execute(self, entities, ctx):
            raise RuntimeError("boom")

    registry.register(Boom())  # type: ignore[arg-type]
    r = registry.execute("BOOM", {}, actx)
    assert not r.success and r.error == "internal_error"


def test_second_person():
    assert second_person("call my friend") == "call your friend"
