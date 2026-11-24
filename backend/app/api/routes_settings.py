"""User settings."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.settings import NovaSettings, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=NovaSettings)
def get_settings(db: Session = Depends(get_db)) -> NovaSettings:
    return settings_service.get_settings(db)


@router.put("/settings", response_model=NovaSettings)
def put_settings(update: SettingsUpdate, db: Session = Depends(get_db)) -> NovaSettings:
    try:
        return settings_service.update_settings(db, update)
    except (ValidationError, ValueError) as exc:
        errors = exc.errors() if isinstance(exc, ValidationError) else [{"msg": str(exc)}]
        raise HTTPException(status_code=422, detail=[{"msg": e["msg"], "loc": e.get("loc", [])} for e in errors]) from exc


@router.post("/settings/reset", response_model=NovaSettings)
def reset_settings(db: Session = Depends(get_db)) -> NovaSettings:
    return settings_service.reset_settings(db)
