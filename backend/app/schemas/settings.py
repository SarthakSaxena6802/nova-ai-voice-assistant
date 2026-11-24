from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NovaSettings(BaseModel):
    """User-adjustable preferences (persisted in SQLite)."""

    # General
    assistant_name: str = Field("Nova", min_length=1, max_length=30)
    user_name: str = Field("", max_length=40)
    theme: Literal["dark", "light"] = "dark"

    # Voice
    voice_enabled: bool = True
    voice_name: str = Field("", max_length=200)
    speech_rate: float = Field(1.0, ge=0.5, le=2.0)
    auto_send_voice: bool = True
    wake_word_enabled: bool = True

    # Decision engine
    execute_threshold: float = Field(0.75, ge=0.05, le=1.0)
    clarify_threshold: float = Field(0.45, ge=0.0, le=0.95)
    context_timeout_seconds: int = Field(120, ge=15, le=900)

    @model_validator(mode="after")
    def _check_thresholds(self) -> "NovaSettings":
        if self.clarify_threshold >= self.execute_threshold:
            raise ValueError("clarify_threshold must be lower than execute_threshold")
        return self


class SettingsUpdate(BaseModel):
    """Partial update – every field optional."""

    assistant_name: str | None = None
    user_name: str | None = None
    theme: Literal["dark", "light"] | None = None
    voice_enabled: bool | None = None
    voice_name: str | None = None
    speech_rate: float | None = None
    auto_send_voice: bool | None = None
    wake_word_enabled: bool | None = None
    execute_threshold: float | None = None
    clarify_threshold: float | None = None
    context_timeout_seconds: int | None = None
