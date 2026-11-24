"""Builds and holds the long-lived services (model, registry, context, knowledge base)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.actions.registry import ActionRegistry, build_default_registry
from app.context.manager import ContextManager
from app.core.config import Settings
from app.core.logging import get_logger
from app.engine.pipeline import AssistantPipeline
from app.ml.intent_classifier import IntentClassifier
from app.services.knowledge_base import KnowledgeBase

log = get_logger("container")


@dataclass
class Container:
    settings: Settings
    classifier: IntentClassifier
    registry: ActionRegistry
    contexts: ContextManager
    knowledge_base: KnowledgeBase
    pipeline: AssistantPipeline
    started_at: float = field(default_factory=time.time)


def build_container(settings: Settings) -> Container:
    classifier = IntentClassifier()
    if not settings.model_path.exists() and settings.auto_train_if_missing:
        log.warning("No trained model found – training one now (python ml/train_model.py does the same)")
        try:
            from app.ml.trainer import train_and_save

            train_and_save(settings.dataset_path, settings.model_path, settings.model_report_path, settings.unseen_dataset_path)
        except Exception:
            log.exception("Automatic training failed")
    classifier.load(settings.model_path)

    kb = KnowledgeBase()
    kb.load(settings.knowledge_base_path)
    registry = build_default_registry()
    contexts = ContextManager()
    pipeline = AssistantPipeline(classifier, registry, contexts, kb, settings.open_browser_on_server)
    return Container(settings, classifier, registry, contexts, kb, pipeline)
