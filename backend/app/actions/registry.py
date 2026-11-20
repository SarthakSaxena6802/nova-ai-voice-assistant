"""Central action registry: maps an approved intent to its handler and guarantees that a
failing handler can never crash the request."""
from __future__ import annotations

from typing import Any

from app.actions.base import ActionContext, ActionResult, BaseAction
from app.actions.basic import CalculatorAction, DateAction, GreetingAction, TimeAction
from app.actions.external import ConversationAction, WeatherAction, WebsiteAction
from app.actions.tasks import FocusAction, ReminderAction, TimerAction
from app.core.logging import get_logger

log = get_logger("actions.registry")


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, BaseAction] = {}

    def register(self, action: BaseAction) -> None:
        self._actions[action.intent] = action

    def get(self, intent: str) -> BaseAction | None:
        return self._actions.get(intent)

    def has(self, intent: str) -> bool:
        return intent in self._actions

    def all(self) -> list[BaseAction]:
        return list(self._actions.values())

    def execute(self, intent: str, entities: dict[str, Any], ctx: ActionContext) -> ActionResult:
        action = self._actions.get(intent)
        if action is None:
            return ActionResult(success=False, action=intent, message="I don't have a skill for that yet.", error="no_handler")
        try:
            result = action.execute(entities, ctx)
            log.info("Action %s → success=%s", intent, result.success)
            return result
        except Exception:
            log.exception("Action %s raised an unexpected error", intent)
            try:
                ctx.db.rollback()
            except Exception:  # pragma: no cover
                pass
            return ActionResult(
                success=False, action=intent, message="Sorry, something went wrong while doing that.", error="internal_error"
            )


def build_default_registry() -> ActionRegistry:
    registry = ActionRegistry()
    for action in (
        GreetingAction(), TimeAction(), DateAction(), CalculatorAction(), TimerAction(), ReminderAction(),
        FocusAction(), WebsiteAction(), WeatherAction(), ConversationAction(),
    ):
        registry.register(action)
    return registry
