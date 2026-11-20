"""Actions that touch the outside world: websites, weather, conversational answers."""
from __future__ import annotations

import webbrowser
from typing import Any

from app.actions.base import ActionContext, ActionResult, BaseAction
from app.core.logging import get_logger
from app.nlp.websites import SAFE_WEBSITES, is_allowed_url
from app.services import weather_service
from app.services.llm.base import LLMError
from app.services.weather_service import WeatherError, WeatherNotConfigured

log = get_logger("actions")


class WebsiteAction(BaseAction):
    intent = "OPEN_WEBSITE"
    name = "Open websites"
    description = "Opens well-known websites from a fixed allow-list. Never runs arbitrary URLs or commands."
    examples = ["Open YouTube", "Launch GitHub", "Go to Wikipedia"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        url, name = entities.get("url"), entities.get("website")
        if not url or not is_allowed_url(url):
            options = ", ".join(w.name for w in list(SAFE_WEBSITES.values())[:8])
            return self.fail(f"I can only open websites from my safe list, like {options}.", "not_allowed")
        opened_by = "client"
        if ctx.open_browser_on_server:
            try:
                if webbrowser.open(url, new=2):
                    opened_by = "server"
            except Exception:  # no browser available – the UI will open the link instead
                log.warning("Could not open browser on server; delegating to client")
        return self.ok(f"Opening {name}.", {"url": url, "website": name, "opened_by": opened_by})


class WeatherAction(BaseAction):
    intent = "WEATHER_QUERY"
    name = "Weather"
    description = "Current conditions and tomorrow's forecast via Open-Meteo (needs internet; set a default city in Settings)."
    examples = ["What's the weather like?", "Will it rain tomorrow?", "Weather in London"]
    requires = ["internet"]

    def available(self, ctx_info: dict[str, Any]) -> tuple[bool, str]:
        if not weather_service.is_enabled():
            return False, "Disabled on the server"
        if not ctx_info.get("weather_city"):
            return True, "Ask with a city, or set a default city in Settings"
        return True, f"Default city: {ctx_info['weather_city']}"

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        city = entities.get("city") or ctx.prefs.weather_city
        day = entities.get("day", "today")
        try:
            report = weather_service.get_weather(city, day, ctx.prefs.temperature_unit)
        except WeatherNotConfigured as exc:
            return self.fail(
                f"{exc} Set a default city in Settings, or ask something like 'what's the weather in London'.",
                "weather_not_configured",
            )
        except WeatherError as exc:
            return self.fail(str(exc), "weather_unavailable")
        u = report.unit
        rain = ""
        if report.precipitation_probability is not None:
            chance = f"{report.precipitation_probability:.0f}"
            article = "an" if chance.startswith("8") or chance in ("11", "18") else "a"
            rain = f", with {article} {chance}% chance of precipitation"
        if day == "tomorrow":
            msg = (
                f"Tomorrow in {report.city} expect {report.description}, with a high of {report.temp_max:.0f}{u} "
                f"and a low of {report.temp_min:.0f}{u}{rain}."
            )
        else:
            msg = (
                f"Right now in {report.city} it's {report.temperature:.0f}{u} and {report.description}"
                f"{f', feeling like {report.feels_like:.0f}{u}' if report.feels_like is not None else ''}. "
                f"Today's high is {report.temp_max:.0f}{u} and the low is {report.temp_min:.0f}{u}{rain}."
            )
        return self.ok(msg, {"weather": report.as_dict()})


class ConversationAction(BaseAction):
    intent = "ASK_QUESTION"
    name = "Questions"
    description = (
        "General questions. Uses an optional AI provider (Claude or a local Ollama model) when configured; "
        "otherwise answers from an offline AI/ML knowledge base and says so when it doesn't know."
    )
    examples = ["Explain machine learning", "What is a confusion matrix?", "Why is the sky blue?"]
    requires = ["llm (optional)"]

    STRONG_MATCH = 0.6

    def available(self, ctx_info: dict[str, Any]) -> tuple[bool, str]:
        if ctx_info.get("llm_configured"):
            return True, f"AI provider: {ctx_info.get('llm_provider')}"
        return True, "Offline knowledge base (no AI provider configured)"

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        question = entities.get("question") or ctx.text
        kb_hit = ctx.knowledge_base.lookup(question) if ctx.knowledge_base else None

        if kb_hit and kb_hit.similarity >= self.STRONG_MATCH:
            return self.ok(kb_hit.answer, {"source": "knowledge_base", "topic": kb_hit.title, "similarity": kb_hit.similarity})

        llm_error = None
        if ctx.llm and ctx.prefs.llm_enabled and ctx.llm.is_configured():
            try:
                answer = ctx.llm.answer(question, ctx.prefs.assistant_name)
                return self.ok(answer, {"source": "llm", "provider": ctx.llm.name, "model": ctx.llm.model})
            except LLMError as exc:
                llm_error = str(exc)
                log.warning("LLM provider failed: %s", exc)

        if kb_hit:
            return self.ok(kb_hit.answer, {"source": "knowledge_base", "topic": kb_hit.title, "similarity": kb_hit.similarity})

        reason = llm_error or "No conversational AI provider is configured"
        return self.fail(
            "I'm not able to answer open questions like that right now — "
            + ("my AI provider isn't reachable. " if llm_error else "no conversational AI is configured, and it isn't in my offline knowledge base. ")
            + "I can still tell the time and date, do calculations, set timers and reminders, start focus mode, open websites, or check the weather.",
            "no_answer",
            {"source": "none", "reason": reason},
        )
