#!/usr/bin/env python3
"""Learned router baseline for Scientific Learning Skills.

Model: character n-gram TF-IDF + Logistic Regression.
This is intentionally lightweight: it runs on CPU, trains quickly, and gives a
strong baseline before moving to embedding or transformer models.
"""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
except ImportError as exc:  # pragma: no cover - exercised only without optional dependency
    raise SystemExit(
        "scikit-learn is required for ml_router. Install with: python -m pip install scikit-learn"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "training" / "router_training_v0.3.jsonl"
DEFAULT_ARTIFACT = PROJECT_ROOT / "artifacts" / "router_model_v0.3.pkl"
DEFAULT_REPORT = PROJECT_ROOT / "artifacts" / "router_model_v0.3_report.json"


@dataclass(frozen=True)
class RouterDataset:
    texts: list[str]
    labels: list[str]
    records: list[dict[str, Any]]


def load_dataset(path: Path = DEFAULT_DATASET) -> RouterDataset:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not record.get("text") or not record.get("label"):
                raise ValueError(f"{path}:{line_no}: record requires text and label")
            records.append(record)
    return RouterDataset(
        texts=[record["text"] for record in records],
        labels=[record["label"] for record in records],
        records=records,
    )


def build_model(seed: int = 42) -> Pipeline:
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(2, 5),
                    min_df=1,
                    sublinear_tf=True,
                    lowercase=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=4.0,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="saga",
                ),
            ),
        ]
    )


def _split_indices(labels: list[str], test_size: float, seed: int) -> tuple[list[int], list[int]]:
    indices = list(range(len(labels)))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=test_size,
        random_state=seed,
        stratify=labels,
    )
    return list(train_idx), list(test_idx)


def _subset(items: list[Any], indices: list[int]) -> list[Any]:
    return [items[i] for i in indices]


def evaluate_predictions(
    expected: list[str],
    predicted: list[str],
    labels: list[str],
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "accuracy": accuracy_score(expected, predicted),
        "macro_f1": f1_score(expected, predicted, average="macro"),
        "weighted_f1": f1_score(expected, predicted, average="weighted"),
        "classification_report": classification_report(
            expected,
            predicted,
            labels=labels,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": {
            "labels": labels,
            "matrix": confusion_matrix(expected, predicted, labels=labels).tolist(),
        },
    }
    if records:
        hard_indices = [i for i, record in enumerate(records) if record.get("hard_negative")]
        non_learning_indices = [i for i, label in enumerate(expected) if label == "non-learning"]
        if hard_indices:
            hard_expected = _subset(expected, hard_indices)
            hard_predicted = _subset(predicted, hard_indices)
            report["hard_negative"] = {
                "total": len(hard_indices),
                "accuracy": accuracy_score(hard_expected, hard_predicted),
                "macro_f1": f1_score(hard_expected, hard_predicted, average="macro"),
            }
        if non_learning_indices:
            nl_expected = _subset(expected, non_learning_indices)
            nl_predicted = _subset(predicted, non_learning_indices)
            true_positive = sum(1 for pred in nl_predicted if pred == "non-learning")
            report["non_learning"] = {
                "total": len(non_learning_indices),
                "recall": true_positive / len(non_learning_indices),
            }
    return report


def train_model(
    dataset_path: Path = DEFAULT_DATASET,
    artifact_path: Path = DEFAULT_ARTIFACT,
    report_path: Path = DEFAULT_REPORT,
    seed: int = 42,
    test_size: float = 0.2,
) -> dict[str, Any]:
    dataset = load_dataset(dataset_path)
    labels = sorted(set(dataset.labels))
    train_idx, test_idx = _split_indices(dataset.labels, test_size, seed)

    train_texts = _subset(dataset.texts, train_idx)
    train_labels = _subset(dataset.labels, train_idx)
    test_texts = _subset(dataset.texts, test_idx)
    test_labels = _subset(dataset.labels, test_idx)
    test_records = _subset(dataset.records, test_idx)

    model = build_model(seed)
    model.fit(train_texts, train_labels)
    predictions = list(model.predict(test_texts))

    metrics = evaluate_predictions(test_labels, predictions, labels, test_records)
    payload = {
        "model_type": "tfidf_char_ngram_logistic_regression",
        "dataset": str(dataset_path),
        "labels": labels,
        "seed": seed,
        "test_size": test_size,
        "train_total": len(train_texts),
        "test_total": len(test_texts),
        "metrics": metrics,
    }

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_path.open("wb") as f:
        pickle.dump({"model": model, "metadata": payload}, f)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def evaluate_model(
    dataset_path: Path = DEFAULT_DATASET,
    artifact_path: Path = DEFAULT_ARTIFACT,
    seed: int = 42,
    test_size: float = 0.2,
) -> dict[str, Any]:
    dataset = load_dataset(dataset_path)
    labels = sorted(set(dataset.labels))
    _, test_idx = _split_indices(dataset.labels, test_size, seed)
    test_texts = _subset(dataset.texts, test_idx)
    test_labels = _subset(dataset.labels, test_idx)
    test_records = _subset(dataset.records, test_idx)

    model, metadata = load_model(artifact_path)
    predicted = list(model.predict(test_texts))
    return {
        "artifact": str(artifact_path),
        "dataset": str(dataset_path),
        "trained_dataset": metadata.get("dataset"),
        "test_total": len(test_texts),
        "metrics": evaluate_predictions(test_labels, predicted, labels, test_records),
    }


def load_model(path: Path = DEFAULT_ARTIFACT) -> tuple[Pipeline, dict[str, Any]]:
    with path.open("rb") as f:
        payload = pickle.load(f)
    return payload["model"], payload["metadata"]


def predict(text: str, model_path: Path = DEFAULT_ARTIFACT, top_k: int = 3) -> dict[str, Any]:
    model, metadata = load_model(model_path)
    label = str(model.predict([text])[0])
    result: dict[str, Any] = {
        "text": text,
        "label": label,
        "model": metadata["model_type"],
    }
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba([text])[0]
        labels = list(model.classes_)
        ranked = sorted(zip(labels, probabilities), key=lambda item: item[1], reverse=True)[:top_k]
        result["top_k"] = [{"label": label, "probability": float(prob)} for label, prob in ranked]
    return result


def route(text: str, model_path: Path = DEFAULT_ARTIFACT, min_confidence: float = 0.35) -> dict[str, Any]:
    """Predict with model confidence and route low-confidence cases to fallback.

    The fallback is still machine-readable. A caller can then ask a short
    clarification question or use the deterministic router.
    """

    result = predict(text, model_path=model_path, top_k=3)
    top = result.get("top_k", [])
    confidence = top[0]["probability"] if top else 1.0
    result["confidence"] = confidence
    result["needs_fallback"] = confidence < min_confidence
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train or run the learned Scientific Learning router.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="train the router model")
    train_parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    train_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    train_parser.add_argument("--report", default=str(DEFAULT_REPORT))
    train_parser.add_argument("--seed", type=int, default=42)
    train_parser.add_argument("--test-size", type=float, default=0.2)

    predict_parser = subparsers.add_parser("predict", help="predict a route")
    predict_parser.add_argument("text")
    predict_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    predict_parser.add_argument("--top-k", type=int, default=3)
    predict_parser.add_argument("--min-confidence", type=float, default=0.35)

    eval_parser = subparsers.add_parser("evaluate", help="evaluate a saved router model")
    eval_parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    eval_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    eval_parser.add_argument("--seed", type=int, default=42)
    eval_parser.add_argument("--test-size", type=float, default=0.2)

    args = parser.parse_args(argv)

    if args.command == "train":
        report = train_model(
            dataset_path=Path(args.dataset),
            artifact_path=Path(args.artifact),
            report_path=Path(args.report),
            seed=args.seed,
            test_size=args.test_size,
        )
        summary = {
            "artifact": args.artifact,
            "report": args.report,
            "train_total": report["train_total"],
            "test_total": report["test_total"],
            "accuracy": report["metrics"]["accuracy"],
            "macro_f1": report["metrics"]["macro_f1"],
            "hard_negative": report["metrics"].get("hard_negative"),
            "non_learning": report["metrics"].get("non_learning"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if args.command == "evaluate":
        report = evaluate_model(
            dataset_path=Path(args.dataset),
            artifact_path=Path(args.artifact),
            seed=args.seed,
            test_size=args.test_size,
        )
        summary = {
            "artifact": report["artifact"],
            "dataset": report["dataset"],
            "test_total": report["test_total"],
            "accuracy": report["metrics"]["accuracy"],
            "macro_f1": report["metrics"]["macro_f1"],
            "hard_negative": report["metrics"].get("hard_negative"),
            "non_learning": report["metrics"].get("non_learning"),
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    result = route(args.text, model_path=Path(args.artifact), min_confidence=args.min_confidence)
    if args.top_k != 3:
        result = predict(args.text, model_path=Path(args.artifact), top_k=args.top_k)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
