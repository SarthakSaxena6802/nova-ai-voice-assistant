"""Provider abstraction for optional conversational AI.

The rest of Nova only depends on ``LLMProvider``; adding a new backend means adding one
class and one line in ``factory.py``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

SYSTEM_PROMPT = (
    "You are {name}, a friendly voice assistant running on the user's computer. "
    "Your answers are read aloud, so reply in plain conversational sentences: no markdown, "
    "no bullet points, no code blocks. Keep answers short — two to four sentences — unless the "
    "user explicitly asks for more detail. If you are not sure about something, say so."
)


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    name: str = "base"

    @property
    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def answer(self, question: str, assistant_name: str = "Nova") -> str:
        """Return a short spoken-style answer or raise ``LLMError``."""

    def describe(self) -> dict[str, object]:
        return {"provider": self.name, "model": self.model, "configured": self.is_configured()}
