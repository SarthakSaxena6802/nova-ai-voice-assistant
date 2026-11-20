"""Conversation history + anonymised analytics events."""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import AnalyticsEvent, Interaction
from app.schemas.assistant import ProcessResponse

log = get_logger("history")


def record(db: Session, r: ProcessResponse) -> int | None:
    """Persist one processed command. A database failure is logged but never breaks the reply."""
    try:
        interaction = Interaction(
            created_at=r.timestamp,
            session_id=r.session_id,
            source=r.source,
            raw_input=r.input,
            normalized_input=r.normalized,
            intent=r.intent,
            confidence=r.confidence,
            alternatives=[a.model_dump() for a in r.top_intents],
            entities=r.entities,
            decision=r.decision,
            decision_reason=r.decision_reason,
            action=r.action,
            response=r.response,
            success=r.success,
            context_used=r.context_used,
            processing_ms=r.processing_ms,
            trace={
                "predicted_intent": r.predicted_intent,
                "model_input": r.model_input,
                "thresholds": r.thresholds.model_dump(),
                "explanation": [e.model_dump() for e in r.explanation],
                "pipeline": [s.model_dump() for s in r.pipeline],
                "missing_entities": r.missing_entities,
                "notes": r.notes,
            },
        )
        db.add(interaction)
        db.add(
            AnalyticsEvent(
                created_at=r.timestamp,
                source=r.source,
                intent=r.intent,
                confidence=r.confidence,
                decision=r.decision,
                success=r.success,
                context_used=bool(r.context_used),
                processing_ms=r.processing_ms,
            )
        )
        db.commit()
        return interaction.id
    except Exception:
        db.rollback()
        log.exception("Failed to store interaction")
        return None


def list_history(db: Session, limit: int = 50, offset: int = 0, intent: str | None = None, decision: str | None = None,
                 search: str | None = None) -> tuple[list[Interaction], int]:
    stmt = select(Interaction)
    if intent:
        stmt = stmt.where(Interaction.intent == intent)
    if decision:
        stmt = stmt.where(Interaction.decision == decision)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(Interaction.raw_input).like(like) | func.lower(Interaction.response).like(like))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Interaction.id.desc()).offset(offset).limit(limit))
    return list(rows), total


def clear_history(db: Session) -> int:
    result = db.execute(delete(Interaction))
    db.commit()
    return result.rowcount or 0


def clear_analytics(db: Session) -> int:
    result = db.execute(delete(AnalyticsEvent))
    db.commit()
    return result.rowcount or 0
