"""Intent classifier tests: loading, predictions on unseen text, confidence output."""
from __future__ import annotations

import json

import pytest

from app.ml.intent_classifier import IntentClassifier, ModelNotLoadedError
from app.nlp.preprocessing import normalize_text, prepare_for_classifier

EXPECTED_INTENTS = {
    "GREETING", "GET_TIME", "GET_DATE", "CALCULATE", "SET_TIMER", "CREATE_REMINDER",
    "FOCUS_MODE", "WEATHER_QUERY", "OPEN_WEBSITE", "ASK_QUESTION", "UNKNOWN",
}


def test_model_loads_with_all_intents(classifier):
    assert classifier.is_loaded
    assert set(classifier.classes) == EXPECTED_INTENTS
    assert classifier.metadata["metrics"]["accuracy"] > 0.8


def test_missing_model_is_reported_not_crashing(tmp_path):
    clf = IntentClassifier()
    clf.load(tmp_path / "does-not-exist.joblib")
    assert not clf.is_loaded
    assert "not found" in clf.load_error
    with pytest.raises(ModelNotLoadedError):
        clf.predict("hello")


@pytest.mark.parametrize(
    "text,intent",
    [
        ("Nova, set a timer for 10 minutes", "SET_TIMER"),
        ("Could you start a countdown for five minutes?", "SET_TIMER"),
        ("Can you open YouTube for me?", "OPEN_WEBSITE"),
        ("what's the time right now", "GET_TIME"),
        ("which date is it today", "GET_DATE"),
        ("what is 72 divided by 8", "CALCULATE"),
        ("remind me to buy eggs at 6 pm", "CREATE_REMINDER"),
        ("I want to concentrate for an hour", "FOCUS_MODE"),
        ("is it going to rain in london", "WEATHER_QUERY"),
        ("explain how decision trees work", "ASK_QUESTION"),
        ("hey nova good evening", "GREETING"),
        ("order me a pizza", "UNKNOWN"),
    ],
)
def test_predicts_unseen_sentences(classifier, text, intent):
    p = classifier.predict(text)
    assert p.intent == intent, [(s.intent, round(s.confidence, 2)) for s in p.top(3)]


def test_prediction_returns_probability_distribution(classifier):
    p = classifier.predict("set a timer for 5 minutes")
    assert 0.0 <= p.confidence <= 1.0
    assert p.confidence == p.ranking[0].confidence
    assert abs(sum(s.confidence for s in p.ranking) - 1.0) < 1e-6
    assert [s.confidence for s in p.ranking] == sorted((s.confidence for s in p.ranking), reverse=True)
    assert len(p.top(3)) == 3


def test_explanation_lists_contributing_features(classifier):
    p = classifier.predict("set a timer for 5 minutes")
    assert p.explanation, "expected feature contributions"
    assert any("timer" in f.feature for f in p.explanation)
    assert all(f.weight > 0 for f in p.explanation)


def test_gibberish_gets_low_confidence_or_unknown(classifier):
    for text in ["qwertyuiop zxcv", "purple monkey dishwasher", "I am bored"]:
        p = classifier.predict(text)
        assert p.intent == "UNKNOWN" or p.confidence < 0.6, (text, p.intent, p.confidence)


def test_unseen_evaluation_file_accuracy(classifier, settings):
    data = json.loads(settings.unseen_dataset_path.read_text(encoding="utf-8"))["examples"]
    correct = sum(classifier.predict(row["text"]).intent == row["intent"] for row in data)
    assert correct / len(data) >= 0.85


def test_preprocessing_is_shared_and_deterministic():
    assert normalize_text("Hey Nova, set a FIVE-minute timer!") == "set a 5 minute timer"
    assert prepare_for_classifier("timer for 45 minutes") == prepare_for_classifier("timer for 7 minutes")
    assert normalize_text("Hello Nova") == "hello"  # name stripped, greeting kept
    assert normalize_text("one hundred and fifty divided by five") == "150 divided by 5"
    assert normalize_text("add twenty and thirty") == "add 20 and 30"
