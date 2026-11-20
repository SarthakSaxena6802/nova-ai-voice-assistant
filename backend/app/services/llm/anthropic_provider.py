"""Claude via the official Anthropic Python SDK.

Enabled with ``NOVA_LLM_PROVIDER=anthropic`` and ``ANTHROPIC_API_KEY`` in the backend .env.
The key is read on the server only; it is never logged or returned to the frontend.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.services.llm.base import SYSTEM_PROMPT, LLMError, LLMProvider

log = get_logger("llm.anthropic")

DEFAULT_MODEL = "claude-opus-5-5"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None, model: str | None = None, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._model = model or DEFAULT_MODEL
        self._timeout = timeout
        self._client = None

    @property
    def model(self) -> str:
        return self._model

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - dependency listed in requirements
                raise LLMError("The 'anthropic' package is not installed.") from exc
            self._client = anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout, max_retries=1)
        return self._client

    def answer(self, question: str, assistant_name: str = "Nova") -> str:
        if not self.is_configured():
            raise LLMError("Anthropic API key is not configured.")
        import anthropic

        client = self._get_client()
        try:
            response = client.beta.messages.create(
                model=self._model,
                max_tokens=1024,  # deliberately short: answers are spoken aloud
                system=SYSTEM_PROMPT.format(name=assistant_name),
                messages=[{"role": "user", "content": question}],
                output_config={"effort": "low"},
                # Server-side refusal fallback: if the model declines, the API retries on a fallback model.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as exc:
            raise LLMError("The Anthropic API key was rejected.") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError("The AI provider is rate-limiting requests. Please try again shortly.") from exc
        except anthropic.APIStatusError as exc:
            log.warning("Anthropic API error status=%s", exc.status_code)
            raise LLMError("The AI provider returned an error.") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("I couldn't reach the AI provider. Check your internet connection.") from exc

        if response.stop_reason == "refusal":
            return "I'm sorry, but I can't help with that request."
        text = " ".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise LLMError("The AI provider returned an empty answer.")
        return text
