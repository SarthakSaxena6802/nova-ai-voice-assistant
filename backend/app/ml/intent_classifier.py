"""Runtime wrapper around the trained scikit-learn pipeline.

Loaded once at backend start-up. Exposes:

* ``predict(text)``  → top intent, confidence, full ranked distribution and an
  explanation (the n-gram features that pushed the decision towards the winning class).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.core.logging import get_logger
from app.nlp.preprocessing import prepare_for_classifier

log = get_logger("ml.classifier")


@dataclass
class IntentScore:
    intent: str
    confidence: float


@dataclass
class FeatureContribution:
    feature: str
    kind: str  # "word" | "char"
    weight: float


@dataclass
class Prediction:
    intent: str
    confidence: float
    ranking: list[IntentScore]
    model_input: str
    explanation: list[FeatureContribution] = field(default_factory=list)
    inference_ms: float = 0.0

    def top(self, k: int = 3) -> list[IntentScore]:
        return self.ranking[:k]


class ModelNotLoadedError(RuntimeError):
    pass


class IntentClassifier:
    def __init__(self) -> None:
        self.pipeline: Any = None
        self.metadata: dict[str, Any] = {}
        self.loaded_at: float | None = None
        self.load_error: str | None = None

    # ------------------------------------------------------------------ loading
    @property
    def is_loaded(self) -> bool:
        return self.pipeline is not None

    @property
    def classes(self) -> list[str]:
        return list(self.pipeline.classes_) if self.is_loaded else []

    def load(self, model_path: Path) -> None:
        try:
            bundle = joblib.load(model_path)
            self.pipeline = bundle["pipeline"]
            self.metadata = bundle.get("metadata", {})
            self.loaded_at = time.time()
            self.load_error = None
            log.info(
                "Intent model loaded: %s | version=%s | classes=%d | test accuracy=%.3f",
                model_path.name,
                self.metadata.get("model_version"),
                len(self.classes),
                self.metadata.get("metrics", {}).get("accuracy", float("nan")),
            )
        except FileNotFoundError:
            self.pipeline = None
            self.load_error = f"Model file not found at {model_path}. Run: python ml/train_model.py"
            log.error(self.load_error)
        except Exception as exc:  # corrupted file, version mismatch, ...
            self.pipeline = None
            self.load_error = f"Failed to load model: {exc}"
            log.exception("Failed to load intent model")

    # --------------------------------------------------------------- inference
    def predict(self, text: str, explain: bool = True) -> Prediction:
        if not self.is_loaded:
            raise ModelNotLoadedError(self.load_error or "Model not loaded")
        start = time.perf_counter()
        model_input = prepare_for_classifier(text)
        probs = self.pipeline.predict_proba([model_input])[0]
        order = np.argsort(probs)[::-1]
        classes = self.pipeline.classes_
        ranking = [IntentScore(str(classes[i]), float(probs[i])) for i in order]
        explanation = self._explain(model_input, int(order[0])) if explain else []
        elapsed = (time.perf_counter() - start) * 1000
        return Prediction(
            intent=ranking[0].intent,
            confidence=ranking[0].confidence,
            ranking=ranking,
            model_input=model_input,
            explanation=explanation,
            inference_ms=round(elapsed, 2),
        )

    def _explain(self, model_input: str, class_index: int, k: int = 6) -> list[FeatureContribution]:
        """Contribution of each active feature = tf-idf value × class coefficient.

        For linear models this is an exact decomposition of the class logit, which makes the
        decision fully inspectable. Word features are preferred because they are readable.
        """
        try:
            features = self.pipeline.named_steps["features"]
            clf = self.pipeline.named_steps["clf"]
            vec = features.transform([model_input]).tocsr()
            names = features.get_feature_names_out()
            coefs = clf.coef_[class_index]
            contributions = []
            for idx, value in zip(vec.indices, vec.data):
                weight = float(value * coefs[idx])
                if weight <= 0:
                    continue
                kind, _, feat = names[idx].partition("__")
                contributions.append(FeatureContribution(feature=feat, kind=kind, weight=round(weight, 4)))
            words = sorted((c for c in contributions if c.kind == "word"), key=lambda c: -c.weight)
            chars = sorted((c for c in contributions if c.kind == "char"), key=lambda c: -c.weight)
            return (words[: k - 2] + chars[:2]) if words else chars[:k]
        except Exception:  # explanation is best-effort, never break inference
            log.debug("Explanation failed", exc_info=True)
            return []
