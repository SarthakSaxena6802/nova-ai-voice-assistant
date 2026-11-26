"""Draw the evaluation charts from artifacts/training_report.json.

Usage (from the backend folder, after `python ml/train_model.py`):

    pip install matplotlib          # once; only needed for these charts, not by the app
    python ml/plot_report.py

Writes PNGs to artifacts/plots/.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")  # render to files, no window
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, to_rgb  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
REPORT = BACKEND / "artifacts" / "training_report.json"
OUT = BACKEND / "artifacts" / "plots"

BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e6e2"
BLUES = LinearSegmentedColormap.from_list("blues", ["#f6f9fd", "#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])

plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": GRID, "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titleweight": "semibold", "axes.titlesize": 13, "figure.dpi": 150,
})


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", OUT / name)


def hbar_labels(ax, bars, fmt="{:.1%}", pad=0.01) -> None:
    for b in bars:
        ax.text(b.get_width() + pad, b.get_y() + b.get_height() / 2, fmt.format(b.get_width()),
                va="center", fontsize=9, color=INK)


def is_dark(rgba) -> bool:
    r, g, b = to_rgb(rgba)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.5


def main() -> None:
    r = json.loads(REPORT.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    m, tm = r["metrics"], r["test_metrics"]
    labels = tm["confusion_matrix"]["labels"]
    cm = np.array(tm["confusion_matrix"]["matrix"])
    subtitle = f"{r['model_name']} · trained {r['trained_at'][:10]} · test set {r['test_size']} sentences"

    # 1. headline metrics
    names = ["Test accuracy", "Macro precision", "Macro recall", "Macro F1", "5-fold CV accuracy", "Unseen phrasings"]
    vals = [m["accuracy"], m["precision_macro"], m["recall_macro"], m["f1_macro"], m["cv_accuracy_mean"], m["unseen_accuracy"]]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    bars = ax.barh(names[::-1], vals[::-1], color=BLUE, height=0.55)
    ax.errorbar(m["cv_accuracy_mean"], 1, xerr=m["cv_accuracy_std"], color=INK2, capsize=4, lw=1)  # CV is row 1 from bottom
    hbar_labels(ax, [b for i, b in enumerate(bars) if i != 1])
    ax.text(m["cv_accuracy_mean"] + m["cv_accuracy_std"] + 0.015, 1, f"{m['cv_accuracy_mean']:.1%} ± {m['cv_accuracy_std']:.1%}", va="center", fontsize=9)
    ax.set_xlim(0, 1.1); ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax.grid(axis="x", color=GRID)
    ax.set_title("Model evaluation — headline metrics", loc="left", pad=22); ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=8, color=INK2)
    save(fig, "01_summary_metrics.png")

    # 2. per-intent precision / recall / F1
    per = tm["per_class"]
    order = sorted(per, key=lambda k: per[k]["f1"])
    y = np.arange(len(order)); h = 0.26
    fig, ax = plt.subplots(figsize=(8, 6))
    for i, (key, color, label) in enumerate([("precision", BLUE, "Precision"), ("recall", ORANGE, "Recall"), ("f1", AQUA, "F1")]):
        ax.barh(y + (1 - i) * h, [per[k][key] for k in order], height=h - 0.03, color=color, label=label)
    for yi, k in zip(y, order):
        ax.text(1.01, yi, f"F1 {per[k]['f1']:.2f}  (n={per[k]['support']})", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y, order); ax.set_xlim(0, 1.25); ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}" if v <= 1 else "")
    ax.grid(axis="x", color=GRID); ax.legend(loc="lower right", frameon=False, ncols=3, bbox_to_anchor=(1, -0.12))
    ax.set_title("Precision, recall and F1 per intent (test set)", loc="left")
    save(fig, "02_per_intent_metrics.png")

    # 3 & 4. confusion matrix — counts and row-normalised (= recall per intent)
    for norm, name, title in [(False, "03_confusion_matrix.png", "Confusion matrix (counts)"),
                              (True, "04_confusion_matrix_normalized.png", "Confusion matrix (row %, = recall)")]:
        data = cm / cm.sum(axis=1, keepdims=True) if norm else cm
        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(data, cmap=BLUES, vmin=0, vmax=1 if norm else data.max())
        for i in range(len(labels)):
            for j in range(len(labels)):
                v = data[i, j]
                if v == 0:
                    continue
                ax.text(j, i, f"{v:.0%}" if norm else str(v), ha="center", va="center", fontsize=9,
                        color="white" if is_dark(im.cmap(im.norm(v))) else INK, fontweight="semibold" if i == j else "normal")
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right"); ax.set_yticks(range(len(labels)), labels)
        ax.set_xlabel("Predicted intent"); ax.set_ylabel("True intent")
        ax.spines[:].set_visible(False); ax.set_xticks(np.arange(len(labels) + 1) - 0.5, minor=True)
        ax.set_yticks(np.arange(len(labels) + 1) - 0.5, minor=True); ax.grid(which="minor", color="white", lw=2)
        ax.tick_params(which="minor", length=0)
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, format=(lambda v, _: f"{v:.0%}") if norm else None)
        ax.set_title(f"{title} — {int(np.trace(cm))}/{int(cm.sum())} correct", loc="left")
        save(fig, name)

    # 5. cross-validation folds
    folds = r["cv_scores"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    bars = ax.bar([f"Fold {i + 1}" for i in range(len(folds))], folds, color=BLUE, width=0.55)
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() - 0.004, f"{b.get_height():.1%}", ha="center", va="top",
                fontsize=9, color="white", fontweight="semibold")
    ax.axhline(m["cv_accuracy_mean"], color=ORANGE, lw=2, ls="--")
    ax.text(-0.45, m["cv_accuracy_mean"] + 0.004, f"mean {m['cv_accuracy_mean']:.1%} ± {m['cv_accuracy_std']:.1%}",
            ha="left", color=ORANGE, fontsize=9, fontweight="semibold")
    ax.set_ylim(0.8, 1.0); ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.02)); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax.grid(axis="y", color=GRID)
    ax.set_title("5-fold cross-validation accuracy (all 449 sentences)", loc="left")
    save(fig, "05_cv_folds.png")

    # 6. dataset balance
    counts = dict(sorted(r["class_counts"].items(), key=lambda kv: kv[1]))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.barh(list(counts), list(counts.values()), color=BLUE, height=0.6)
    hbar_labels(ax, bars, "{:.0f}", pad=0.8)
    ax.set_xlim(0, max(counts.values()) * 1.15); ax.grid(axis="x", color=GRID); ax.set_xlabel("Training sentences")
    ax.set_title(f"Dataset — examples per intent ({r['dataset_size']} total)", loc="left")
    save(fig, "06_class_distribution.png")

    # 7. confidence on never-seen sentences vs the decision thresholds
    ex = sorted(r["unseen_evaluation"]["examples"], key=lambda e: e["confidence"])
    fig, ax = plt.subplots(figsize=(8, 8))
    colors = [BLUE if e["expected"] == e["predicted"] else RED for e in ex]
    ax.barh([f"{e['text'][:38]}  ({e['predicted']})" for e in ex], [e["confidence"] for e in ex], color=colors, height=0.65)
    for x, label in [(0.75, "execute ≥ 75 %"), (0.45, "clarify ≥ 45 %")]:
        ax.axvline(x, color=INK2, ls="--", lw=1); ax.text(x, len(ex) - 0.3, label, ha="center", fontsize=8.5, color=INK2)
    ax.set_xlim(0, 1.02); ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}"); ax.grid(axis="x", color=GRID)
    ax.tick_params(axis="y", labelsize=8)
    wrong = sum(c == RED for c in colors)
    ax.set_title(f"Confidence on {len(ex)} unseen sentences — {len(ex) - wrong} correct" + (f", {wrong} wrong (red)" if wrong else ""), loc="left")
    save(fig, "07_unseen_confidence.png")


if __name__ == "__main__":
    main()
