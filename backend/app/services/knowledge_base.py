"""Offline question answering via TF-IDF retrieval over a small curated knowledge base.

Only answers when the best match is similar enough; otherwise Nova says it doesn't know
instead of guessing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.logging import get_logger
from app.nlp.preprocessing import normalize_text

log = get_logger("knowledge")

MIN_SIMILARITY = 0.35


@dataclass
class KnowledgeAnswer:
    title: str
    answer: str
    similarity: float


class KnowledgeBase:
    def __init__(self) -> None:
        self.entries: list[dict] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    def load(self, path: Path) -> None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.entries = data.get("entries", [])
        except (FileNotFoundError, json.JSONDecodeError):
            log.warning("Knowledge base not found or invalid at %s", path)
            self.entries = []
            return
        docs = [normalize_text(" ".join([e["title"], *e.get("keywords", [])])) for e in self.entries]
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        self._matrix = self._vectorizer.fit_transform(docs)
        log.info("Knowledge base loaded: %d entries", len(self.entries))

    def lookup(self, question: str) -> KnowledgeAnswer | None:
        if not self.entries or self._vectorizer is None:
            return None
        vec = self._vectorizer.transform([normalize_text(question)])
        if vec.nnz == 0:
            return None
        sims = cosine_similarity(vec, self._matrix)[0]
        best = int(sims.argmax())
        if sims[best] < MIN_SIMILARITY:
            return None
        entry = self.entries[best]
        return KnowledgeAnswer(entry["title"], entry["answer"], round(float(sims[best]), 3))
