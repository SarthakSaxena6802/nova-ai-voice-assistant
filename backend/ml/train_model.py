"""Train Nova's intent classifier.

Usage (from the ``backend`` folder, with the virtual environment active)::

    python ml/train_model.py
    python ml/train_model.py --dataset datasets/intents.json --no-refit

The backend loads ``artifacts/intent_model.joblib`` on start-up; restart it (or call
``POST /api/model/reload``) after retraining.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.ml.trainer import train_and_save  # noqa: E402


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Train Nova's intent classifier")
    parser.add_argument("--dataset", type=Path, default=settings.dataset_path)
    parser.add_argument("--unseen", type=Path, default=settings.unseen_dataset_path)
    parser.add_argument("--model-out", type=Path, default=settings.model_path)
    parser.add_argument("--report-out", type=Path, default=settings.model_report_path)
    parser.add_argument("--no-refit", action="store_true", help="Keep the train-split model instead of refitting on all data")
    args = parser.parse_args()

    setup_logging("INFO")
    report = train_and_save(args.dataset, args.model_out, args.report_out, args.unseen, refit_full=not args.no_refit)
    tm = report["test_metrics"]

    print("\n" + "=" * 68)
    print(f" Nova intent classifier — {report['model_name']}")
    print("=" * 68)
    print(f" Dataset: {report['dataset_size']} examples | train {report['train_size']} / test {report['test_size']}")
    print(f" Best C (5-fold CV): {report['hyperparameters']['C']}")
    print(f" Test accuracy:      {tm['accuracy']:.3f}")
    print(f" Macro precision:    {tm['precision_macro']:.3f}")
    print(f" Macro recall:       {tm['recall_macro']:.3f}")
    print(f" Macro F1:           {tm['f1_macro']:.3f}")
    print(f" CV accuracy:        {report['metrics']['cv_accuracy_mean']:.3f} ± {report['metrics']['cv_accuracy_std']:.3f}")
    if report["unseen_evaluation"]:
        print(f" Unseen-phrasing accuracy: {report['unseen_evaluation']['accuracy']:.3f}")
    print("-" * 68)
    print(f" {'intent':18s} {'prec':>6s} {'rec':>6s} {'f1':>6s} {'n':>4s}")
    for label, m in tm["per_class"].items():
        print(f" {label:18s} {m['precision']:6.2f} {m['recall']:6.2f} {m['f1']:6.2f} {m['support']:4d}")
    print("-" * 68)
    labels = tm["confusion_matrix"]["labels"]
    short = [lbl[:5] for lbl in labels]
    print(" Confusion matrix (rows = true, cols = predicted)")
    print(" " + " " * 16 + " ".join(f"{s:>5s}" for s in short))
    for label, row in zip(labels, tm["confusion_matrix"]["matrix"]):
        print(f" {label:16s}" + " ".join(f"{v:5d}" for v in row))
    if report["misclassified_test_examples"]:
        print("-" * 68)
        print(" Misclassified test examples:")
        for m in report["misclassified_test_examples"]:
            print(f"   '{m['text']}'  expected={m['expected']}  predicted={m['predicted']}")
    if report["unseen_evaluation"]:
        wrong = [e for e in report["unseen_evaluation"]["examples"] if e["expected"] != e["predicted"]]
        if wrong:
            print(" Unseen phrasings misclassified:")
            for e in wrong:
                print(f"   '{e['text']}'  expected={e['expected']}  predicted={e['predicted']} ({e['confidence']:.2f})")
    print("=" * 68)
    print(f" Model saved to {args.model_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
