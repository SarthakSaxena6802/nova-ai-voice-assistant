"""Assistant, health, model and capability endpoints."""
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
from app.ml.intent_classifier import ModelNotLoadedError, load_report
from app.schemas.assistant import ProcessRequest, ProcessResponse
from app.services import settings_service, weather_service

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db), c: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    llm = c.llm.describe() if c.llm else {"provider": None, "model": None, "configured": False}
    status = "ok" if db_ok and c.classifier.is_loaded else "degraded"
    return {
        "status": status,
        "app": c.settings.app_name,
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
        "services": {
            "llm": llm,
            "weather": {"enabled": weather_service.is_enabled(), "provider": "Open-Meteo"},
            "knowledge_base": {"entries": len(c.knowledge_base.entries)},
            "open_browser_on_server": c.settings.open_browser_on_server,
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


@router.get("/assistant/capabilities", tags=["assistant"])
def capabilities(db: Session = Depends(get_db), c: Container = Depends(get_container)) -> dict[str, Any]:
    prefs = settings_service.get_settings(db)
    info = {
        "weather_city": prefs.weather_city,
        "llm_configured": bool(c.llm and c.llm.is_configured() and prefs.llm_enabled),
        "llm_provider": c.llm.name if c.llm else None,
    }
    items = []
    for action in c.registry.all():
        available, status = action.available(info)
        items.append(
            {
                "intent": action.intent,
                "name": action.name,
                "description": action.description,
                "examples": action.examples,
                "requires": action.requires,
                "available": available,
                "status": status,
            }
        )
    from app.nlp.websites import SAFE_WEBSITES

    return {
        "capabilities": items,
        "websites": [{"key": w.key, "name": w.name, "url": w.url} for w in SAFE_WEBSITES.values()],
        "intents": c.classifier.classes,
    }


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


@router.post("/model/predict", tags=["model"])
def predict(req: PredictRequest, c: Container = Depends(get_container)) -> dict[str, Any]:
    """Raw classifier output without executing anything (model playground)."""
    try:
        p = c.classifier.predict(req.text)
    except ModelNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "input": req.text,
        "model_input": p.model_input,
        "intent": p.intent,
        "confidence": round(p.confidence, 4),
        "ranking": [{"intent": s.intent, "confidence": round(s.confidence, 4)} for s in p.ranking],
        "explanation": [f.__dict__ for f in p.explanation],
        "inference_ms": p.inference_ms,
    }


@router.get("/model", tags=["model"])
def model_info(c: Container = Depends(get_container)) -> dict[str, Any]:
    return {"info": c.classifier.info(), "report": load_report(c.settings.model_report_path)}


@router.post("/model/reload", tags=["model"])
def reload_model(c: Container = Depends(get_container)) -> dict[str, Any]:
    c.reload_model()
    if not c.classifier.is_loaded:
        raise HTTPException(status_code=500, detail=c.classifier.load_error)
    return {"ok": True, "info": c.classifier.info()}
