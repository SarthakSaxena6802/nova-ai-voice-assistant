"""HTTP API tests through FastAPI's TestClient (full pipeline, real model, temp database)."""
from __future__ import annotations

from datetime import timedelta

from app.core.timeutils import now


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model"]["loaded"] is True
    assert body["database"]["ok"] is True
    assert "api_key" not in r.text.lower()


def test_process_executes_high_confidence_command(say):
    r = say("Could you start a countdown for five minutes?")
    assert r["decision"] == "EXECUTE"
    assert r["intent"] == "SET_TIMER" and r["predicted_intent"] == "SET_TIMER"
    assert r["confidence"] >= r["thresholds"]["execute"]
    assert r["entities"]["duration_seconds"] == 300
    assert r["success"] is True
    assert r["response"] == "Your timer is set for 5 minutes."
    assert len(r["top_intents"]) == 3 and len(r["alternatives"]) == 2
    stages = [s["stage"] for s in r["pipeline"]]
    assert stages[:3] == ["input", "normalize", "classify"] and "action" in stages
    assert r["id"] is not None


def test_process_invalid_input(client):
    assert client.post("/api/assistant/process", json={"text": ""}).status_code == 422
    assert client.post("/api/assistant/process", json={"text": "   "}).status_code == 422
    assert client.post("/api/assistant/process", json={"text": "x" * 501}).status_code == 422
    assert client.post("/api/assistant/process", json={"text": "hi", "source": "telepathy"}).status_code == 422
    assert client.post("/api/assistant/process", json={"text": "hi", "session_id": "../etc"}).status_code == 422
    assert client.post("/api/assistant/process", content=b"not json", headers={"content-type": "application/json"}).status_code == 422


def test_missing_entity_triggers_clarification_and_context(say):
    first = say("Remind me to study tomorrow")
    assert first["decision"] == "CLARIFY"
    assert first["missing_entities"] == ["time"]
    assert first["context"]["pending"]["intent"] == "CREATE_REMINDER"
    second = say("At 8 PM")
    assert second["decision"] == "EXECUTE"
    assert second["context_used"] == "slot_filling"
    assert second["intent"] == "CREATE_REMINDER" and second["success"]
    assert second["entities"]["due_at"].endswith("T20:00:00")
    assert second["entities"]["message"] == "study"


def test_follow_up_modifies_timer(say, client):
    say("Set a timer for 10 minutes")
    r = say("Actually make it 15")
    assert r["context_used"] == "follow_up:SET_TIMER"
    assert r["entities"]["duration_seconds"] == 900 and r["success"]
    timer = client.get("/api/timers").json()
    assert any(t["duration_seconds"] == 900 for t in timer)
    cancel = say("cancel it")
    assert cancel["success"] and cancel["entities"]["operation"] == "cancel"


def test_low_confidence_is_not_executed(say):
    r = say("I am bored")
    assert r["decision"] == "UNKNOWN"
    assert r["action"] is None and r["success"] is False
    assert "rephrase" in r["response"] or "not something I can do" in r["response"]


def test_out_of_scope_is_unknown(say):
    r = say("play some music")
    assert r["decision"] == "UNKNOWN" and r["predicted_intent"] == "UNKNOWN"


def test_medium_confidence_asks_confirmation(say, client):
    # Raise the execute threshold so a normally-executed command lands in the confirm band.
    client.put("/api/settings", json={"execute_threshold": 1.0, "clarify_threshold": 0.3})
    try:
        r = say("what's the weather like")
        assert r["decision"] == "CONFIRM"
        assert r["context"]["pending"]["kind"] == "confirm"
        yes = say("yes")
        assert yes["context_used"] == "confirmation"
        assert yes["intent"] == "WEATHER_QUERY" and yes["decision"] == "EXECUTE"
    finally:
        client.post("/api/settings/reset")


def test_cancel_pending_question(say):
    say("set a timer")
    r = say("never mind")
    assert r["decision"] == "CANCELLED" and r["context"]["pending"] is None


def test_action_failure_is_reported(say):
    r = say("divide 5 by 0")
    assert r["decision"] == "EXECUTE" and r["success"] is False
    assert "divide by zero" in r["response"]


def test_open_website_returns_allowlisted_url(say):
    r = say("Can you open YouTube for me?")
    assert r["success"] and r["data"]["url"] == "https://www.youtube.com"


def test_capabilities(client):
    body = client.get("/api/assistant/capabilities").json()
    intents = {c["intent"] for c in body["capabilities"]}
    assert {"GET_TIME", "SET_TIMER", "CREATE_REMINDER", "OPEN_WEBSITE"} <= intents
    assert any(w["key"] == "github" for w in body["websites"])


def test_timer_and_reminder_endpoints(client):
    t = client.post("/api/timers", json={"duration_seconds": 120, "label": "Eggs"})
    assert t.status_code == 201 and t.json()["remaining_seconds"] > 100
    tid = t.json()["id"]
    assert client.delete(f"/api/timers/{tid}").json()["status"] == "cancelled"
    assert client.delete(f"/api/timers/{tid}").status_code == 409
    assert client.delete("/api/timers/999999").status_code == 404
    assert client.post("/api/timers", json={"duration_seconds": 0}).status_code == 422

    due = (now() + timedelta(hours=3)).isoformat()
    rem = client.post("/api/reminders", json={"message": "Submit report", "due_at": due})
    assert rem.status_code == 201
    rid = rem.json()["id"]
    assert any(x["id"] == rid for x in client.get("/api/reminders").json())
    assert client.patch(f"/api/reminders/{rid}/complete").json()["status"] == "completed"
    assert client.delete(f"/api/reminders/{rid}").json() == {"ok": True}
    past = (now() - timedelta(hours=1)).isoformat()
    assert client.post("/api/reminders", json={"message": "x", "due_at": past}).status_code == 422


def test_focus_endpoints(client):
    client.post("/api/focus/stop")
    s = client.post("/api/focus/start", json={"duration_minutes": 30})
    assert s.status_code == 201 and s.json()["duration_seconds"] == 1800
    assert client.post("/api/focus/start", json={}).status_code == 409
    assert client.get("/api/focus").json()["active"]["id"] == s.json()["id"]
    assert client.post("/api/focus/stop").json()["status"] == "stopped"


def test_settings_persist_and_validate(client):
    r = client.put("/api/settings", json={"assistant_name": "Nova", "speech_rate": 1.3, "weather_city": "Pune"})
    assert r.status_code == 200
    assert client.get("/api/settings").json()["speech_rate"] == 1.3
    bad = client.put("/api/settings", json={"execute_threshold": 0.3, "clarify_threshold": 0.6})
    assert bad.status_code == 422
    assert client.put("/api/settings", json={"theme": "neon"}).status_code == 422
    client.post("/api/settings/reset")


def test_history_and_analytics_reflect_real_usage(client, say):
    say("what time is it")
    hist = client.get("/api/history?limit=5").json()
    assert hist["total"] >= 1 and hist["items"][0]["raw_input"] == "what time is it"
    assert hist["items"][0]["trace"]["pipeline"]
    stats = client.get("/api/analytics").json()
    assert stats["total"] >= 1 and stats["executed"] >= 1
    assert sum(b["count"] for b in stats["confidence_histogram"]) == stats["total"]

    # clearing history keeps anonymous analytics; clearing analytics empties them
    assert client.delete("/api/history").status_code == 200
    assert client.get("/api/history").json()["total"] == 0
    assert client.get("/api/analytics").json()["total"] >= 1
    client.delete("/api/analytics")
    assert client.get("/api/analytics").json() == {"total": 0, "empty": True}


def test_model_endpoints(client):
    info = client.get("/api/model").json()
    assert info["info"]["loaded"] and info["report"]["test_metrics"]["confusion_matrix"]["labels"]
    p = client.post("/api/model/predict", json={"text": "open github"}).json()
    assert p["intent"] == "OPEN_WEBSITE" and len(p["ranking"]) == 11


def test_notifications_flow(client, db):
    from app.services import notification_service

    n = notification_service.create(db, "system", "Test", "hello")
    db.commit()
    unread = client.get("/api/notifications").json()
    assert any(x["id"] == n.id for x in unread)
    client.post(f"/api/notifications/{n.id}/read")
    assert all(x["id"] != n.id for x in client.get("/api/notifications").json())
