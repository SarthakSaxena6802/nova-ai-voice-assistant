"""Training + evaluation procedure for the intent classifier.

1. Load the JSON dataset and apply the same preprocessing used at inference time.
2. Stratified 80/20 train/test split.
3. Choose the regularisation strength ``C`` with 5-fold stratified cross-validation
   on the training split (macro-F1).
4. Evaluate on the held-out test split: accuracy, precision, recall, F1, confusion matrix.
5. Evaluate on a separate "unseen phrasings" file that shares no sentences with the dataset.
6. Refit on the full dataset (standard practice once hyper-parameters are fixed) and save
   the pipeline + metadata with joblib, plus a JSON report for the UI.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split

from app.core.logging import get_logger
from app.ml.model import MODEL_NAME, build_pipeline, load_dataset, prepare_all

log = get_logger("ml.trainer")

C_GRID = [1.0, 3.0, 10.0, 30.0, 100.0, 300.0]
RANDOM_STATE = 42


def _metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    p_macro, r_macro, f_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )
    p_w, r_w, f_w, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="weighted", zero_division=0
    )
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision_macro": round(float(p_macro), 4),
        "recall_macro": round(float(r_macro), 4),
        "f1_macro": round(float(f_macro), 4),
        "precision_weighted": round(float(p_w), 4),
        "recall_weighted": round(float(r_w), 4),
        "f1_weighted": round(float(f_w), 4),
        "per_class": {
            label: {
                "precision": round(float(p[i]), 4),
                "recall": round(float(r[i]), 4),
                "f1": round(float(f[i]), 4),
                "support": int(s[i]),
            }
            for i, label in enumerate(labels)
        },
        "confusion_matrix": {
            "labels": labels,
            "matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        },
    }


def train_and_save(
    dataset_path: Path,
    model_path: Path,
    report_path: Path,
    unseen_path: Path | None = None,
    refit_full: bool = True,
) -> dict[str, Any]:
    ds = load_dataset(dataset_path)
    X = prepare_all(ds.texts)
    y = ds.labels
    labels = sorted(set(y))
    log.info("Loaded %d examples across %d intents", len(X), len(labels))

    X_train, X_test, y_train, y_test, raw_train, raw_test = train_test_split(
        X, y, ds.texts, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    search = GridSearchCV(build_pipeline(), {"clf__C": C_GRID}, cv=cv, scoring="f1_macro", n_jobs=1)
    search.fit(X_train, y_train)
    best_C = float(search.best_params_["clf__C"])
    log.info("Grid search: best C=%s (cv macro-F1=%.4f)", best_C, search.best_score_)

    model = search.best_estimator_
    y_pred = model.predict(X_test)
    test_metrics = _metrics(y_test, list(y_pred), labels)
    test_conf = model.predict_proba(X_test).max(axis=1)

    misclassified = [
        {"text": raw, "expected": exp, "predicted": pred}
        for raw, exp, pred in zip(raw_test, y_test, y_pred)
        if exp != pred
    ]

    cv_scores = cross_val_score(build_pipeline(C=best_C), X, y, cv=cv, scoring="accuracy")

    final_model = build_pipeline(C=best_C).fit(X, y) if refit_full else model

    unseen_report: dict[str, Any] | None = None
    if unseen_path and Path(unseen_path).exists():
        unseen = load_dataset(unseen_path)
        u_pred = final_model.predict(prepare_all(unseen.texts))
        u_conf = final_model.predict_proba(prepare_all(unseen.texts)).max(axis=1)
        unseen_report = {
            "size": len(unseen.texts),
            "accuracy": round(float(accuracy_score(unseen.labels, u_pred)), 4),
            "mean_confidence": round(float(np.mean(u_conf)), 4),
            "examples": [
                {"text": t, "expected": e, "predicted": p, "confidence": round(float(c), 4)}
                for t, e, p, c in zip(unseen.texts, unseen.labels, u_pred, u_conf)
            ],
        }

    version = datetime.now().strftime("%Y%m%d-%H%M%S")
    class_counts = {label: y.count(label) for label in labels}
    metadata = {
        "model_version": version,
        "model_name": MODEL_NAME,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_path": Path(dataset_path).name,
        "dataset_size": len(X),
        "class_counts": class_counts,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "refit_on_full_dataset": refit_full,
        "hyperparameters": {
            "C": best_C,
            "C_grid": C_GRID,
            "cv_best_macro_f1": round(float(search.best_score_), 4),
            "word_ngrams": [1, 2],
            "char_ngrams": [2, 5],
            "class_weight": "balanced",
        },
        "metrics": {
            "accuracy": test_metrics["accuracy"],
            "precision_macro": test_metrics["precision_macro"],
            "recall_macro": test_metrics["recall_macro"],
            "f1_macro": test_metrics["f1_macro"],
            "test_mean_confidence": round(float(np.mean(test_conf)), 4),
            "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
            "cv_accuracy_std": round(float(cv_scores.std()), 4),
            "unseen_accuracy": unseen_report["accuracy"] if unseen_report else None,
        },
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": final_model, "metadata": metadata}, model_path)

    report = {
        **metadata,
        "test_metrics": test_metrics,
        "misclassified_test_examples": misclassified,
        "cv_scores": [round(float(s), 4) for s in cv_scores],
        "unseen_evaluation": unseen_report,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Saved model → %s and report → %s", model_path, report_path)
    return report
