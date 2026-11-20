"""Persisted user settings (key/value rows validated through ``NovaSettings``)."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import SettingEntry
from app.schemas.settings import NovaSettings, SettingsUpdate

log = get_logger("settings")


def get_settings(db: Session) -> NovaSettings:
    stored = {row.key: row.value for row in db.scalars(select(SettingEntry))}
    known = {k: v for k, v in stored.items() if k in NovaSettings.model_fields}
    try:
        return NovaSettings(**known)
    except ValueError:
        log.warning("Stored settings were invalid; falling back to defaults")
        return NovaSettings()


def update_settings(db: Session, update: SettingsUpdate) -> NovaSettings:
    current = get_settings(db).model_dump()
    changes = update.model_dump(exclude_none=True)
    merged = NovaSettings(**{**current, **changes})  # raises ValueError if invalid
    for key, value in merged.model_dump().items():
        row = db.get(SettingEntry, key)
        if row is None:
            db.add(SettingEntry(key=key, value=value))
        elif row.value != value:
            row.value = value
    db.commit()
    log.info("Settings updated: %s", ", ".join(sorted(changes)) or "(none)")
    return merged


def reset_settings(db: Session) -> NovaSettings:
    db.execute(delete(SettingEntry))
    db.commit()
    return NovaSettings()
