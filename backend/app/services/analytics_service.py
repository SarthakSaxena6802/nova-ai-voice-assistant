"""Usage analytics computed from stored ``analytics_events`` (real data only)."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutils import now
from app.models import AnalyticsEvent


def compute(db: Session, days: int = 14) -> dict[str, Any]:
    events = list(db.scalars(select(AnalyticsEvent).order_by(AnalyticsEvent.created_at)))
    total = len(events)
    if total == 0:
        return {"total": 0, "empty": True}

    decisions = Counter(e.decision for e in events)
    intents = Counter(e.intent for e in events)
    sources = Counter(e.source for e in events)
    executed = [e for e in events if e.decision == "EXECUTE"]
    succeeded = sum(1 for e in executed if e.success)

    buckets = [0] * 10
    for e in events:
        buckets[min(int(e.confidence * 10), 9)] += 1

    conf_by_intent: dict[str, list[float]] = defaultdict(list)
    for e in events:
        conf_by_intent[e.intent].append(e.confidence)

    start = (now() - timedelta(days=days - 1)).date()
    per_day: dict[str, dict[str, int]] = {
        (start + timedelta(days=i)).isoformat(): {"total": 0, "executed": 0} for i in range(days)
    }
    for e in events:
        key = e.created_at.date().isoformat()
        if key in per_day:
            per_day[key]["total"] += 1
            per_day[key]["executed"] += int(e.decision == "EXECUTE")

    return {
        "empty": False,
        "total": total,
        "executed": len(executed),
        "successful": succeeded,
        "failed_actions": len(executed) - succeeded,
        "clarifications": decisions.get("CLARIFY", 0) + decisions.get("CONFIRM", 0),
        "confirmations": decisions.get("CONFIRM", 0),
        "missing_info": decisions.get("CLARIFY", 0),
        "unknown": decisions.get("UNKNOWN", 0),
        "cancelled": decisions.get("CANCELLED", 0),
        "context_resolved": sum(1 for e in events if e.context_used),
        "success_rate": round(succeeded / len(executed), 4) if executed else 0.0,
        "execution_rate": round(len(executed) / total, 4),
        "avg_confidence": round(sum(e.confidence for e in events) / total, 4),
        "avg_processing_ms": round(sum(e.processing_ms for e in events) / total, 2),
        "voice_share": round(sources.get("voice", 0) / total, 4),
        "intent_distribution": [{"intent": k, "count": v} for k, v in intents.most_common()],
        "decision_distribution": [{"decision": k, "count": v} for k, v in decisions.most_common()],
        "source_distribution": [{"source": k, "count": v} for k, v in sources.most_common()],
        "confidence_histogram": [
            {"bucket": f"{i / 10:.1f}–{(i + 1) / 10:.1f}", "from": i / 10, "count": c} for i, c in enumerate(buckets)
        ],
        "confidence_by_intent": sorted(
            [{"intent": k, "avg_confidence": round(sum(v) / len(v), 4), "count": len(v)} for k, v in conf_by_intent.items()],
            key=lambda x: -x["count"],
        ),
        "daily": [{"date": k, **v} for k, v in per_day.items()],
    }
