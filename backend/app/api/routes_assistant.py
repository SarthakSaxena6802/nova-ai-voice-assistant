"""Health and assistant endpoints."""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_container
from app.core.config import APP_VERSION
from app.core.container import Container
from app.database.session import get_db
from app.ml.intent_classifier import ModelNotLoadedError
from app.schemas.assistant import ProcessRequest, ProcessResponse

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db), c: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok and c.classifier.is_loaded else "degraded",
        "version": APP_VERSION,
        "uptime_seconds": int(time.time() - c.started_at),
        "database": {"ok": db_ok},
        "model": {
            "loaded": c.classifier.is_loaded,
            "version": c.classifier.metadata.get("model_version"),
            "name": c.classifier.metadata.get("model_name"),
            "accuracy": c.classifier.metadata.get("metrics", {}).get("accuracy"),
            "error": c.classifier.load_error,
        },
    }


@router.post("/assistant/process", response_model=ProcessResponse, tags=["assistant"])
def process(req: ProcessRequest, db: Session = Depends(get_db), c: Container = Depends(get_container)) -> ProcessResponse:
    try:
        return c.pipeline.process(db, req)
    except ModelNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=f"The intent model is not loaded. {exc}") from exc


class ResetContextRequest(BaseModel):
    session_id: str = Field("default", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")


@router.post("/assistant/reset-context", tags=["assistant"])
def reset_context(req: ResetContextRequest, c: Container = Depends(get_container)) -> dict[str, bool]:
    c.contexts.reset(req.session_id)
    return {"ok": True}
