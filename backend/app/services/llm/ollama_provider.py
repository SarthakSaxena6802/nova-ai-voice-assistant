"""Local LLM via Ollama (https://ollama.com) – free and fully offline.

Enabled with ``NOVA_LLM_PROVIDER=ollama`` (and optionally ``NOVA_LLM_MODEL=llama3.2``).
"""
from __future__ import annotations

import httpx

from app.core.logging import get_logger
from app.services.llm.base import SYSTEM_PROMPT, LLMError, LLMProvider

log = get_logger("llm.ollama")

DEFAULT_MODEL = "llama3.2"


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str | None = None, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model or DEFAULT_MODEL
        self._timeout = timeout

    @property
    def model(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._base_url)

    def answer(self, question: str, assistant_name: str = "Nova") -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.format(name=assistant_name)},
                {"role": "user", "content": question},
            ],
        }
        try:
            resp = httpx.post(f"{self._base_url}/api/chat", json=payload, timeout=self._timeout)
            resp.raise_for_status()
            text = (resp.json().get("message") or {}).get("content", "").strip()
        except httpx.ConnectError as exc:
            raise LLMError("Ollama is not running. Start it with 'ollama serve'.") from exc
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("Ollama request failed: %s", exc.__class__.__name__)
            raise LLMError("The local AI model returned an error.") from exc
        if not text:
            raise LLMError("The local AI model returned an empty answer.")
        return text
