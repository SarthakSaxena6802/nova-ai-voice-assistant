"""History, analytics and settings."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.settings import NovaSettings, SettingsUpdate
from app.services import analytics_service, history_service, settings_service

router = APIRouter(prefix="/api")


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    session_id: str
    source: str
    raw_input: str
    normalized_input: str
    intent: str
    confidence: float
    alternatives: list[dict[str, Any]]
    entities: dict[str, Any]
    decision: str
    decision_reason: str
    action: str | None
    response: str
    success: bool
    context_used: str | None
    processing_ms: float
    trace: dict[str, Any]


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


@router.get("/history", response_model=HistoryPage, tags=["history"])
def history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    intent: str | None = None,
    decision: str | None = None,
    search: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),
) -> HistoryPage:
    rows, total = history_service.list_history(db, limit, offset, intent, decision, search)
    return HistoryPage(items=[HistoryItem.model_validate(r) for r in rows], total=total, limit=limit, offset=offset)


@router.delete("/history", tags=["history"])
def clear_history(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"deleted": history_service.clear_history(db)}


@router.get("/analytics", tags=["analytics"])
def analytics(days: int = Query(14, ge=1, le=90), db: Session = Depends(get_db)) -> dict[str, Any]:
    return analytics_service.compute(db, days)


@router.delete("/analytics", tags=["analytics"])
def clear_analytics(db: Session = Depends(get_db)) -> dict[str, int]:
    return {"deleted": history_service.clear_analytics(db)}


@router.get("/settings", response_model=NovaSettings, tags=["settings"])
def get_settings(db: Session = Depends(get_db)) -> NovaSettings:
    return settings_service.get_settings(db)


@router.put("/settings", response_model=NovaSettings, tags=["settings"])
def put_settings(update: SettingsUpdate, db: Session = Depends(get_db)) -> NovaSettings:
    try:
        return settings_service.update_settings(db, update)
    except (ValidationError, ValueError) as exc:
        errors = exc.errors() if isinstance(exc, ValidationError) else [{"msg": str(exc)}]
        raise HTTPException(status_code=422, detail=[{"msg": e["msg"], "loc": e.get("loc", [])} for e in errors]) from exc


@router.post("/settings/reset", response_model=NovaSettings, tags=["settings"])
def reset_settings(db: Session = Depends(get_db)) -> NovaSettings:
    return settings_service.reset_settings(db)
