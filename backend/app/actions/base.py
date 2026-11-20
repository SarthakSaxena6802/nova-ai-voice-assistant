"""Action interface.

Every capability implements ``BaseAction.execute(entities, ctx) -> ActionResult``. Actions
validate their own parameters, never raise to the caller (the registry wraps them), and
return structured results the API can serialise directly.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.schemas.settings import NovaSettings

if TYPE_CHECKING:
    from app.services.knowledge_base import KnowledgeBase
    from app.services.llm.base import LLMProvider


class ActionResult(BaseModel):
    success: bool
    action: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    # Stored as conversation context so follow-ups ("make it 15", "cancel it") can refer to it
    context: dict[str, Any] | None = None


@dataclass
class ActionContext:
    db: Session
    prefs: NovaSettings
    now: datetime
    text: str = ""
    knowledge_base: "KnowledgeBase | None" = None
    llm: "LLMProvider | None" = None
    open_browser_on_server: bool = False
    last_action: dict[str, Any] | None = None
    extras: dict[str, Any] = field(default_factory=dict)


class BaseAction(ABC):
    intent: str = ""
    name: str = ""
    description: str = ""
    examples: list[str] = []
    requires: list[str] = []  # e.g. ["internet"], ["llm (optional)"]

    @abstractmethod
    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult: ...

    def available(self, ctx_info: dict[str, Any]) -> tuple[bool, str]:
        return True, "Ready"

    # helpers
    def ok(self, message: str, data: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> ActionResult:
        return ActionResult(success=True, action=self.intent, message=message, data=data or {}, context=context)

    def fail(self, message: str, error: str = "failed", data: dict[str, Any] | None = None) -> ActionResult:
        return ActionResult(success=False, action=self.intent, message=message, error=error, data=data or {})


_PRONOUNS = {"my": "your", "me": "you", "i": "you", "mine": "yours", "myself": "yourself", "am": "are", "our": "your", "we": "you"}


def second_person(text: str) -> str:
    """'call my friend' -> 'call your friend' (for spoken confirmations)."""
    return re.sub(r"\b(my|me|i|mine|myself|am|our|we)\b", lambda m: _PRONOUNS[m.group(1)], text)
