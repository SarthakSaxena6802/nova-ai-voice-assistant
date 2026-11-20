from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.llm.anthropic_provider import AnthropicProvider
from app.services.llm.base import LLMProvider
from app.services.llm.ollama_provider import OllamaProvider

log = get_logger("llm")


def create_provider(settings: Settings) -> LLMProvider | None:
    name = settings.llm_provider.strip().lower()
    if not name:
        log.info("Conversational AI provider: none (offline knowledge base only)")
        return None
    if name == "anthropic":
        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        provider: LLMProvider = AnthropicProvider(key, settings.llm_model or None, settings.llm_timeout_seconds)
    elif name == "ollama":
        provider = OllamaProvider(settings.ollama_base_url, settings.llm_model or None, settings.llm_timeout_seconds)
    else:
        log.warning("Unknown NOVA_LLM_PROVIDER '%s' – conversational AI disabled", name)
        return None
    log.info(
        "Conversational AI provider: %s (model=%s, configured=%s)", provider.name, provider.model, provider.is_configured()
    )
    return provider
