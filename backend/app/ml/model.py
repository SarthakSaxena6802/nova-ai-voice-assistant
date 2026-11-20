"""Model definition + dataset loading for Nova's intent classifier.

Architecture (scikit-learn ``Pipeline``)::

    prepared text ──┬── word TF-IDF (1–2 grams) ──┐
                    └── char TF-IDF (2–5 grams) ──┴─► FeatureUnion ─► LogisticRegression (softmax)

* Word n-grams capture phrasing ("set a", "remind me", "what time").
* Character n-grams make the model robust to typos and speech-recognition errors
  ("timmer", "whether", "you tube").
* Multinomial logistic regression outputs a calibrated-ish probability distribution
  over all intents, which the decision engine uses as its confidence score.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline

from app.nlp.preprocessing import prepare_for_classifier

MODEL_NAME = "TF-IDF (word + char n-grams) + Logistic Regression"


@dataclass
class Dataset:
    texts: list[str]
    labels: list[str]
    intents: list[str]


def load_dataset(path: Path) -> Dataset:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    examples = data["examples"] if isinstance(data, dict) else data
    texts, labels = [], []
    for row in examples:
        text, intent = str(row.get("text", "")).strip(), str(row.get("intent", "")).strip()
        if text and intent:
            texts.append(text)
            labels.append(intent)
    intents = data.get("intents") if isinstance(data, dict) else None
    return Dataset(texts=texts, labels=labels, intents=intents or sorted(set(labels)))


def prepare_all(texts: list[str]) -> list[str]:
    return [prepare_for_classifier(t) for t in texts]


def build_pipeline(C: float = 10.0) -> Pipeline:
    features = FeatureUnion(
        [
            ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)),
        ]
    )
    clf = LogisticRegression(C=C, max_iter=5000, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])
