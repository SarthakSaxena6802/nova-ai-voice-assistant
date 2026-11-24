"""Actions that reach outside Nova: opening websites and answering questions."""
from __future__ import annotations

import webbrowser
from typing import Any

from app.actions.base import ActionContext, ActionResult, BaseAction
from app.core.logging import get_logger
from app.nlp.websites import SAFE_WEBSITES, is_allowed_url

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


class ConversationAction(BaseAction):
    intent = "ASK_QUESTION"
    name = "Questions"
    description = "Answers general questions from a small offline AI/ML knowledge base, and says so when it doesn't know."
    examples = ["Explain machine learning", "What is a confusion matrix?", "Why is the sky blue?"]

    def execute(self, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        question = entities.get("question") or ctx.text
        hit = ctx.knowledge_base.lookup(question) if ctx.knowledge_base else None
        if hit:
            return self.ok(hit.answer, {"source": "knowledge_base", "topic": hit.title, "similarity": hit.similarity})
        return self.fail(
            "I don't know the answer to that — it isn't in my offline knowledge base. "
            "I can tell the time and date, do calculations, set timers and reminders, or open websites.",
            "no_answer",
            {"source": "none"},
        )
