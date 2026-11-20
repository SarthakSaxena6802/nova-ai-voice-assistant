from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Decision = Literal["EXECUTE", "CONFIRM", "CLARIFY", "UNKNOWN", "CANCELLED"]


class ProcessRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    source: Literal["text", "voice", "quick_action"] = "text"
    session_id: str = Field("default", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        return v


class IntentScoreOut(BaseModel):
    intent: str
    confidence: float


class FeatureOut(BaseModel):
    feature: str
    kind: str
    weight: float


class PipelineStep(BaseModel):
    stage: str
    title: str
    detail: str
    status: Literal["ok", "warn", "error", "skip"] = "ok"
    ms: float | None = None


class Thresholds(BaseModel):
    execute: float
    clarify: float


class ProcessResponse(BaseModel):
    id: int | None = None
    timestamp: datetime
    session_id: str
    source: str
    input: str
    normalized: str
    model_input: str
    intent: str
    confidence: float
    predicted_intent: str
    top_intents: list[IntentScoreOut]
    alternatives: list[IntentScoreOut]
    explanation: list[FeatureOut]
    entities: dict[str, Any]
    missing_entities: list[str]
    thresholds: Thresholds
    decision: Decision
    decision_reason: str
    action: str | None
    response: str
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    context_used: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    pipeline: list[PipelineStep]
    processing_ms: float
