#!/usr/bin/env python3
"""Learned router baseline for Scientific Learning Skills.

The train-time model is character n-gram TF-IDF + Logistic Regression. Saved
models use a small, versioned JSON schema (optionally gzip-compressed) instead
of pickle. Loading an artifact therefore parses data and never executes Python
objects from the artifact.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import platform
import re
import stat
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Sequence

_SKLEARN_IMPORT_ERROR: ImportError | None = None
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import GroupShuffleSplit, train_test_split
    from sklearn.pipeline import Pipeline
except ImportError as exc:  # pragma: no cover - depends on the caller's environment
    _SKLEARN_IMPORT_ERROR = exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_ROOT = Path(__file__).resolve().parent / "resources"


def _training_output(filename: str) -> Path:
    """Keep routine training outputs separate from checked-in benchmark resources."""

    if (PROJECT_ROOT / "pyproject.toml").is_file():
        return PROJECT_ROOT / "artifacts" / "generated" / filename
    return Path.cwd() / "artifacts" / "generated" / filename


DEFAULT_DATASET = RESOURCE_ROOT / "data" / "training" / "router_training_v0.3.jsonl"
DEFAULT_ARTIFACT = RESOURCE_ROOT / "artifacts" / "router_model_v0.3.json.gz"
DEFAULT_REPORT = RESOURCE_ROOT / "artifacts" / "router_model_v0.3_report.json"
DEFAULT_TRAIN_ARTIFACT = _training_output("router_model_v0.3.json.gz")
DEFAULT_TRAIN_REPORT = _training_output("router_model_v0.3_report.json")

ARTIFACT_FORMAT = "scientific-learning-router"
ARTIFACT_SCHEMA_VERSION = 2
MAX_COMPRESSED_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_UNCOMPRESSED_ARTIFACT_BYTES = 128 * 1024 * 1024
MAX_ROUTER_TEXT_CHARS = 20_000
MAX_ARTIFACT_FEATURES = 250_000
MAX_ARTIFACT_CLASSES = 128
MAX_ARTIFACT_COEFFICIENTS = 2_000_000
MAX_BENCHMARK_REPORT_BYTES = 4 * 1024 * 1024
DEFAULT_EVAL_SEED = 42
DEFAULT_EVAL_TEST_SIZE = 0.2
DEFAULT_EVAL_SPLIT_GROUP = "topic"
_WHITE_SPACES = re.compile(r"\s\s+")
EXPECTED_ROUTER_LABELS = {
    "deepening-learning",
    "fuzzy-understanding",
    "mistake-review",
    "non-learning",
    "problem-solving",
    "study-plan-builder",
    "text-memorizer",
    "word-deep-dive",
    "zero-base-learning",
}


class MLDependencyError(RuntimeError):
    """Raised when a train/evaluate command lacks the optional ML stack."""


class RouterArtifactError(ValueError):
    """Raised when a router artifact is unsafe, corrupt, or unsupported."""


class RouterBenchmarkError(ValueError):
    """Raised when an external evaluation split is corrupt or incompatible."""


def _validate_router_text(text: str) -> None:
    if not isinstance(text, str):
        raise TypeError(f"router input must be str, got {type(text).__name__}")
    if not text.strip():
        raise ValueError("router input must not be empty")
    if len(text) > MAX_ROUTER_TEXT_CHARS:
        raise ValueError(
            f"router input has {len(text)} characters; limit is {MAX_ROUTER_TEXT_CHARS}"
        )


@dataclass(frozen=True)
class RouterDataset:
    texts: list[str]
    labels: list[str]
    records: list[dict[str, Any]]


@dataclass(frozen=True)
class PortableRouterModel:
    """Minimal inference implementation for the exported sklearn pipeline."""

    vocabulary: dict[str, int]
    idf: tuple[float, ...]
    classes_: tuple[str, ...]
    coefficients: tuple[tuple[float, ...], ...]
    intercepts: tuple[float, ...]
    ngram_range: tuple[int, int]
    lowercase: bool
    sublinear_tf: bool

    def _features(self, text: str) -> list[tuple[int, float]]:
        _validate_router_text(text)

        document = text.lower() if self.lowercase else text
        document = _WHITE_SPACES.sub(" ", document)
        min_n, max_n = self.ngram_range
        counts: Counter[int] = Counter()
        document_length = len(document)
        for n in range(min_n, min(max_n + 1, document_length + 1)):
            for start in range(document_length - n + 1):
                index = self.vocabulary.get(document[start : start + n])
                if index is not None:
                    counts[index] += 1

        weighted: list[tuple[int, float]] = []
        squared_norm = 0.0
        for index, count in counts.items():
            term_frequency = 1.0 + math.log(count) if self.sublinear_tf else float(count)
            value = term_frequency * self.idf[index]
            weighted.append((index, value))
            squared_norm += value * value

        if squared_norm == 0.0:
            return []
        inverse_norm = 1.0 / math.sqrt(squared_norm)
        return [(index, value * inverse_norm) for index, value in weighted]

    def _decision_scores(self, text: str) -> list[float]:
        features = self._features(text)
        return [
            self.intercepts[class_index]
            + sum(row[feature_index] * value for feature_index, value in features)
            for class_index, row in enumerate(self.coefficients)
        ]

    def predict(self, texts: Sequence[str]) -> list[str]:
        predictions: list[str] = []
        for text in texts:
            scores = self._decision_scores(text)
            best_index = max(range(len(scores)), key=scores.__getitem__)
            predictions.append(self.classes_[best_index])
        return predictions

    def predict_proba(self, texts: Sequence[str]) -> list[list[float]]:
        probabilities: list[list[float]] = []
        for text in texts:
            scores = self._decision_scores(text)
            maximum = max(scores)
            exponentials = [math.exp(score - maximum) for score in scores]
            total = sum(exponentials)
            probabilities.append([value / total for value in exponentials])
        return probabilities


def _require_sklearn(action: str) -> None:
    if _SKLEARN_IMPORT_ERROR is not None:
        raise MLDependencyError(
            f"scikit-learn is required to {action}. Install the ML extra with: "
            'python -m pip install -e ".[ml]"'
        ) from _SKLEARN_IMPORT_ERROR


def _dependency_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for distribution in ("numpy", "scipy", "scikit-learn"):
        try:
            versions[distribution] = package_version(distribution)
        except PackageNotFoundError:
            versions[distribution] = "not-installed"
    return versions


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _record_keys(dataset: RouterDataset) -> list[str]:
    keys: list[str] = []
    for index, record in enumerate(dataset.records):
        record_id = record.get("id")
        if record_id is None:
            digest = hashlib.sha256(
                f"{index}\0{record['text']}\0{record['label']}".encode("utf-8")
            ).hexdigest()
            key = f"derived:{digest}"
        elif not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"router dataset record {index + 1} id must be a non-empty string")
        else:
            key = record_id.strip()
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise ValueError("router dataset record ids/derived keys must be unique")
    return keys


def _reject_colliding_training_paths(
    dataset_path: Path, artifact_path: Path, report_path: Path
) -> None:
    """Prevent model/report writes from overwriting inputs or each other."""

    def same_target(left: Path, right: Path) -> bool:
        same = left.resolve(strict=False) == right.resolve(strict=False)
        if not same and left.exists() and right.exists():
            try:
                same = os.path.samefile(left, right)
            except OSError:
                same = False
        return same

    named_paths = {
        "dataset": Path(dataset_path),
        "artifact": Path(artifact_path),
        "report": Path(report_path),
    }
    items = list(named_paths.items())
    for left_index, (left_name, left_path) in enumerate(items):
        for right_name, right_path in items[left_index + 1 :]:
            if same_target(left_path, right_path):
                raise ValueError(
                    f"training {left_name} and {right_name} paths must be different: "
                    f"{left_path}"
                )

    protected = {
        "checked-in artifact": DEFAULT_ARTIFACT,
        "frozen benchmark report": DEFAULT_REPORT,
    }
    for output_name, output_path in (("artifact", Path(artifact_path)), ("report", Path(report_path))):
        for protected_name, protected_path in protected.items():
            if same_target(output_path, protected_path):
                raise ValueError(
                    f"refusing to overwrite {protected_name} with training {output_name}: "
                    f"{protected_path}; train into {PROJECT_ROOT / 'artifacts' / 'generated'} "
                    "and promote reviewed files separately"
                )


def load_dataset(path: Path = DEFAULT_DATASET) -> RouterDataset:
    records: list[dict[str, Any]] = []
    try:
        stream = path.open(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"router dataset not found: {path}") from exc

    with stream:
        for line_no, line in enumerate(stream, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(record, dict) or not record.get("text") or not record.get("label"):
                raise ValueError(f"{path}:{line_no}: record requires non-empty text and label")
            if not isinstance(record["text"], str) or not isinstance(record["label"], str):
                raise ValueError(f"{path}:{line_no}: text and label must be strings")
            records.append(record)

    if not records:
        raise ValueError(f"router dataset is empty: {path}")
    return RouterDataset(
        texts=[record["text"] for record in records],
        labels=[record["label"] for record in records],
        records=records,
    )


def build_model(seed: int = 42) -> Any:
    _require_sklearn("train the learned router")
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


def _validate_test_size(test_size: float) -> None:
    if not 0.0 < test_size < 1.0:
        raise ValueError(f"test_size must be between 0 and 1, got {test_size}")


def _record_split_indices(
    labels: list[str], test_size: float, seed: int
) -> tuple[list[int], list[int], dict[str, Any]]:
    _require_sklearn("split the router dataset")
    indices = list(range(len(labels)))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=test_size,
        random_state=seed,
        stratify=labels,
    )
    return list(train_idx), list(test_idx), {
        "strategy": "stratified_record_holdout",
        "group_field": None,
        "leakage_resistant": False,
        "limitation": "Records generated from the same topic/template family may appear in both partitions.",
    }


def _group_split_indices(
    dataset: RouterDataset,
    test_size: float,
    seed: int,
    group_field: str,
    candidate_splits: int = 128,
) -> tuple[list[int], list[int], dict[str, Any]]:
    """Select a deterministic group-disjoint split with balanced labels.

    If a label has only one raw group, a true group holdout is mathematically
    impossible for that label. Those records use stable record-id groups, and
    the exception is made explicit in the returned metadata.
    """

    _require_sklearn("split the router dataset")
    raw_groups: list[str] = []
    groups_by_label: dict[str, set[str]] = defaultdict(set)
    for index, (record, label) in enumerate(zip(dataset.records, dataset.labels)):
        value = record.get(group_field)
        if value is None or str(value).strip() == "":
            raise ValueError(
                f"record {record.get('id', index)!r} has no non-empty {group_field!r} split group"
            )
        group = str(value)
        raw_groups.append(group)
        groups_by_label[label].add(group)

    fallback_labels = {
        label: sorted(groups)
        for label, groups in groups_by_label.items()
        if len(groups) < 2
    }
    effective_groups: list[str] = []
    for index, (record, label, group) in enumerate(
        zip(dataset.records, dataset.labels, raw_groups)
    ):
        if label in fallback_labels:
            stable_id = str(record.get("id") or f"row-{index}")
            effective_groups.append(f"record-id:{stable_id}")
        else:
            effective_groups.append(f"{group_field}:{group}")

    labels = sorted(set(dataset.labels))
    label_totals = Counter(dataset.labels)
    splitter = GroupShuffleSplit(
        n_splits=candidate_splits,
        test_size=test_size,
        random_state=seed,
    )
    best: tuple[float, int, list[int], list[int]] | None = None
    for candidate_index, (train_array, test_array) in enumerate(
        splitter.split(dataset.texts, dataset.labels, effective_groups)
    ):
        train_idx = list(train_array)
        test_idx = list(test_array)
        if set(_subset(dataset.labels, train_idx)) != set(labels):
            continue
        if set(_subset(dataset.labels, test_idx)) != set(labels):
            continue
        test_counts = Counter(_subset(dataset.labels, test_idx))
        size_error = abs(len(test_idx) / len(dataset.labels) - test_size)
        label_error = sum(
            abs(test_counts[label] / label_totals[label] - test_size) for label in labels
        ) / len(labels)
        score = size_error + label_error
        candidate = (score, candidate_index, train_idx, test_idx)
        if best is None or candidate[:2] < best[:2]:
            best = candidate

    if best is None:
        raise ValueError(
            f"could not create a {group_field!r} group split containing every label in both "
            "partitions; choose --split-group none or improve group coverage"
        )

    score, selected_candidate, train_idx, test_idx = best
    train_effective = {effective_groups[index] for index in train_idx}
    test_effective = {effective_groups[index] for index in test_idx}
    train_raw = {raw_groups[index] for index in train_idx}
    test_raw = {raw_groups[index] for index in test_idx}
    fallback = {
        label: {
            "reason": "label has fewer than two unique raw groups",
            "raw_groups": groups,
            "effective_strategy": "record_id",
        }
        for label, groups in sorted(fallback_labels.items())
    }
    metadata: dict[str, Any] = {
        "strategy": "balanced_group_holdout",
        "group_field": group_field,
        "leakage_resistant": len(fallback) == 0,
        "candidate_splits": candidate_splits,
        "selected_candidate": selected_candidate,
        "balance_error": score,
        "effective_group_overlap_count": len(train_effective & test_effective),
        "raw_group_overlap": sorted(train_raw & test_raw),
        "train_group_count": len(train_effective),
        "test_group_count": len(test_effective),
        "fallbacks": fallback,
    }
    if fallback:
        metadata["limitation"] = (
            "Some labels have only one raw group, so those labels use record-id groups. "
            "See fallbacks and raw_group_overlap; this is not a fully group-disjoint benchmark."
        )
    return train_idx, test_idx, metadata


def _split_indices(
    dataset: RouterDataset,
    test_size: float,
    seed: int,
    split_group: str | None,
) -> tuple[list[int], list[int], dict[str, Any]]:
    _validate_test_size(test_size)
    if split_group in (None, "none"):
        return _record_split_indices(dataset.labels, test_size, seed)
    return _group_split_indices(dataset, test_size, seed, split_group)


def _subset(items: Sequence[Any], indices: list[int]) -> list[Any]:
    return [items[i] for i in indices]


def evaluate_predictions(
    expected: list[str],
    predicted: list[str],
    labels: list[str],
    records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    _require_sklearn("evaluate router predictions")
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
            nl_predicted = _subset(predicted, non_learning_indices)
            true_positive = sum(1 for prediction in nl_predicted if prediction == "non-learning")
            report["non_learning"] = {
                "total": len(non_learning_indices),
                "recall": true_positive / len(non_learning_indices),
            }
    return report


def _portable_payload(model: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    vectorizer = model.named_steps["tfidf"]
    classifier = model.named_steps["clf"]
    features = [str(feature) for feature in vectorizer.get_feature_names_out()]
    classes = [str(label) for label in classifier.classes_]
    coefficients = classifier.coef_.tolist()
    if len(coefficients) != len(classes):
        raise RouterArtifactError(
            "portable export currently requires a multiclass classifier with one coefficient row per class"
        )
    return {
        "format": ARTIFACT_FORMAT,
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "metadata": metadata,
        "vectorizer": {
            "analyzer": "char",
            "features": features,
            "idf": vectorizer.idf_.tolist(),
            "lowercase": bool(vectorizer.lowercase),
            "ngram_range": list(vectorizer.ngram_range),
            "norm": vectorizer.norm,
            "sublinear_tf": bool(vectorizer.sublinear_tf),
        },
        "classifier": {
            "classes": classes,
            "coefficients": coefficients,
            "intercepts": classifier.intercept_.tolist(),
            "probability": "multinomial_softmax",
        },
    }


def _number_list(value: Any, field: str, expected_length: int | None = None) -> tuple[float, ...]:
    if not isinstance(value, list):
        raise RouterArtifactError(f"artifact field {field!r} must be a list")
    if expected_length is not None and len(value) != expected_length:
        raise RouterArtifactError(
            f"artifact field {field!r} has {len(value)} values; expected {expected_length}"
        )
    numbers: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise RouterArtifactError(f"artifact field {field!r} contains a non-number")
        number = float(item)
        if not math.isfinite(number):
            raise RouterArtifactError(f"artifact field {field!r} contains a non-finite number")
        numbers.append(number)
    return tuple(numbers)


def _metadata_positive_int(metadata: dict[str, Any], field: str) -> int:
    value = metadata.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise RouterArtifactError(f"artifact metadata.{field} must be a positive integer")
    return value


def _validate_artifact_metadata(metadata: dict[str, Any], classes: list[str]) -> None:
    if set(classes) != EXPECTED_ROUTER_LABELS:
        missing = sorted(EXPECTED_ROUTER_LABELS - set(classes))
        unexpected = sorted(set(classes) - EXPECTED_ROUTER_LABELS)
        raise RouterArtifactError(
            f"artifact classes do not match project router labels; "
            f"missing={missing}, unexpected={unexpected}"
        )
    if metadata.get("model_type") != "tfidf_char_ngram_logistic_regression":
        raise RouterArtifactError("artifact metadata.model_type is unsupported")
    labels = metadata.get("labels")
    if not isinstance(labels, list) or labels != sorted(EXPECTED_ROUTER_LABELS):
        raise RouterArtifactError("artifact metadata.labels must match the sorted project labels")
    dataset_sha256 = metadata.get("dataset_sha256")
    if not isinstance(dataset_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", dataset_sha256):
        raise RouterArtifactError("artifact metadata.dataset_sha256 must be a lowercase SHA-256")
    if not isinstance(metadata.get("dataset"), str) or not metadata["dataset"].strip():
        raise RouterArtifactError("artifact metadata.dataset must be a non-empty string")
    seed = metadata.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise RouterArtifactError("artifact metadata.seed must be an integer")
    test_size = metadata.get("test_size")
    if isinstance(test_size, bool) or not isinstance(test_size, (int, float)):
        raise RouterArtifactError("artifact metadata.test_size must be numeric")
    if not math.isfinite(float(test_size)) or not 0.0 < float(test_size) < 1.0:
        raise RouterArtifactError("artifact metadata.test_size must be between 0 and 1")

    dataset_total = _metadata_positive_int(metadata, "dataset_total")
    train_total = _metadata_positive_int(metadata, "train_total")
    test_total = _metadata_positive_int(metadata, "test_total")
    if train_total + test_total != dataset_total:
        raise RouterArtifactError("artifact metadata train_total + test_total must equal dataset_total")

    holdout_ids = metadata.get("holdout_record_ids")
    if not isinstance(holdout_ids, list) or len(holdout_ids) != test_total:
        raise RouterArtifactError(
            "artifact metadata.holdout_record_ids must contain exactly test_total entries"
        )
    if not all(isinstance(item, str) and 0 < len(item) <= 256 for item in holdout_ids):
        raise RouterArtifactError("artifact holdout record ids must be non-empty strings up to 256 chars")
    if len(set(holdout_ids)) != len(holdout_ids):
        raise RouterArtifactError("artifact holdout record ids must be unique")

    if not isinstance(metadata.get("split"), dict):
        raise RouterArtifactError("artifact metadata.split must be an object")
    if not isinstance(metadata.get("training_config"), dict):
        raise RouterArtifactError("artifact metadata.training_config must be an object")
    dependencies = metadata.get("training_dependencies")
    if not isinstance(dependencies, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in dependencies.items()
    ):
        raise RouterArtifactError("artifact metadata.training_dependencies must map strings to strings")
    if not isinstance(metadata.get("evaluation_scope"), str):
        raise RouterArtifactError("artifact metadata.evaluation_scope must be a string")


def _model_from_payload(payload: Any) -> tuple[PortableRouterModel, dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RouterArtifactError("router artifact root must be a JSON object")
    if payload.get("format") != ARTIFACT_FORMAT:
        raise RouterArtifactError(
            f"unsupported router artifact format {payload.get('format')!r}; expected {ARTIFACT_FORMAT!r}"
        )
    if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise RouterArtifactError(
            f"unsupported router artifact schema {payload.get('schema_version')!r}; "
            f"this version supports schema {ARTIFACT_SCHEMA_VERSION}"
        )

    metadata = payload.get("metadata")
    vectorizer = payload.get("vectorizer")
    classifier = payload.get("classifier")
    if not isinstance(metadata, dict):
        raise RouterArtifactError("artifact metadata must be a JSON object")
    if not isinstance(vectorizer, dict) or not isinstance(classifier, dict):
        raise RouterArtifactError("artifact requires vectorizer and classifier objects")

    if vectorizer.get("analyzer") != "char" or vectorizer.get("norm") != "l2":
        raise RouterArtifactError("artifact uses an unsupported vectorizer (expected char analyzer + l2 norm)")
    ngram_range = vectorizer.get("ngram_range")
    if (
        not isinstance(ngram_range, list)
        or len(ngram_range) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in ngram_range)
        or ngram_range != [2, 5]
    ):
        raise RouterArtifactError("artifact vectorizer.ngram_range must be [2, 5] for schema version 1")

    if not isinstance(vectorizer.get("lowercase"), bool) or not isinstance(
        vectorizer.get("sublinear_tf"), bool
    ):
        raise RouterArtifactError("artifact vectorizer lowercase/sublinear_tf fields must be booleans")

    features = vectorizer.get("features")
    if not isinstance(features, list) or not features or not all(isinstance(item, str) for item in features):
        raise RouterArtifactError("artifact vectorizer.features must be a non-empty string list")
    if len(features) > MAX_ARTIFACT_FEATURES:
        raise RouterArtifactError(
            f"artifact has {len(features)} features; limit is {MAX_ARTIFACT_FEATURES}"
        )
    if any(not 2 <= len(feature) <= 5 for feature in features):
        raise RouterArtifactError("artifact vectorizer features must be character 2-5 grams")
    if len(set(features)) != len(features):
        raise RouterArtifactError("artifact vectorizer.features contains duplicate entries")
    feature_count = len(features)
    idf = _number_list(vectorizer.get("idf"), "vectorizer.idf", feature_count)

    classes = classifier.get("classes")
    if not isinstance(classes, list) or not 2 <= len(classes) <= MAX_ARTIFACT_CLASSES or not all(
        isinstance(item, str) and item for item in classes
    ):
        raise RouterArtifactError(
            f"artifact classifier.classes must contain 2-{MAX_ARTIFACT_CLASSES} non-empty labels"
        )
    if len(set(classes)) != len(classes):
        raise RouterArtifactError("artifact classifier.classes contains duplicates")
    _validate_artifact_metadata(metadata, classes)
    coefficient_values = classifier.get("coefficients")
    if not isinstance(coefficient_values, list) or len(coefficient_values) != len(classes):
        raise RouterArtifactError("artifact classifier.coefficients must have one row per class")
    coefficient_count = len(classes) * feature_count
    if coefficient_count > MAX_ARTIFACT_COEFFICIENTS:
        raise RouterArtifactError(
            f"artifact has {coefficient_count} coefficients; limit is "
            f"{MAX_ARTIFACT_COEFFICIENTS}"
        )
    coefficients = tuple(
        _number_list(row, f"classifier.coefficients[{index}]", feature_count)
        for index, row in enumerate(coefficient_values)
    )
    intercepts = _number_list(classifier.get("intercepts"), "classifier.intercepts", len(classes))
    if classifier.get("probability") != "multinomial_softmax":
        raise RouterArtifactError("artifact uses an unsupported probability transform")

    model = PortableRouterModel(
        vocabulary={feature: index for index, feature in enumerate(features)},
        idf=idf,
        classes_=tuple(classes),
        coefficients=coefficients,
        intercepts=intercepts,
        ngram_range=(ngram_range[0], ngram_range[1]),
        lowercase=bool(vectorizer.get("lowercase")),
        sublinear_tf=bool(vectorizer.get("sublinear_tf")),
    )
    return model, dict(metadata)


def _validate_artifact_extension(path: Path) -> None:
    lower_name = path.name.lower()
    if lower_name.endswith((".pkl", ".pickle", ".joblib")):
        raise RouterArtifactError(
            f"refusing unsafe legacy model artifact {path}: pickle/joblib loading can execute code "
            "and is version-brittle. Retrain it as .json.gz with: "
            f"python -m learning_agent.ml_router train --artifact {DEFAULT_TRAIN_ARTIFACT}"
        )
    if not (lower_name.endswith(".json") or lower_name.endswith(".json.gz")):
        raise RouterArtifactError("router artifact must use the safe .json or .json.gz format")


def _encode_artifact(payload: dict[str, Any], compressed: bool) -> bytes:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if not compressed:
        return serialized
    output = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=output, mode="wb", compresslevel=9, mtime=0) as stream:
        stream.write(serialized)
    return output.getvalue()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    _validate_artifact_extension(path)
    encoded = _encode_artifact(payload, compressed=path.name.lower().endswith(".gz"))
    _atomic_write(path, encoded)


def _read_artifact(path: Path) -> Any:
    _validate_artifact_extension(path)
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise RouterArtifactError(f"router artifact must be a regular file: {path}")
        if file_stat.st_size > MAX_COMPRESSED_ARTIFACT_BYTES:
            raise RouterArtifactError(
                f"router artifact is {file_stat.st_size} bytes; "
                f"limit is {MAX_COMPRESSED_ARTIFACT_BYTES}"
            )
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            raw = stream.read(MAX_COMPRESSED_ARTIFACT_BYTES + 1)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"router artifact not found: {path}. Train it with: "
            f"python -m learning_agent.ml_router train --artifact {path}"
        ) from exc
    except OSError as exc:
        raise RouterArtifactError(f"unable to read router artifact {path}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(raw) > MAX_COMPRESSED_ARTIFACT_BYTES:
        raise RouterArtifactError(
            f"router artifact exceeds {MAX_COMPRESSED_ARTIFACT_BYTES} bytes"
        )

    try:
        if path.name.lower().endswith(".gz"):
            with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
                decoded = stream.read(MAX_UNCOMPRESSED_ARTIFACT_BYTES + 1)
        else:
            decoded = raw
    except (OSError, EOFError) as exc:
        raise RouterArtifactError(f"router artifact is corrupt or not valid gzip: {path}: {exc}") from exc
    if len(decoded) > MAX_UNCOMPRESSED_ARTIFACT_BYTES:
        raise RouterArtifactError(
            f"decompressed router artifact exceeds {MAX_UNCOMPRESSED_ARTIFACT_BYTES} bytes"
        )
    try:
        return json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouterArtifactError(f"router artifact is not valid UTF-8 JSON: {path}: {exc}") from exc


def _read_benchmark_report(path: Path) -> dict[str, Any]:
    """Read a bounded, data-only report used as the external holdout source."""

    if path.suffix.lower() != ".json":
        raise RouterBenchmarkError("benchmark report must use the .json format")
    descriptor: int | None = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise RouterBenchmarkError(f"benchmark report must be a regular file: {path}")
        if file_stat.st_size > MAX_BENCHMARK_REPORT_BYTES:
            raise RouterBenchmarkError(
                f"benchmark report is {file_stat.st_size} bytes; "
                f"limit is {MAX_BENCHMARK_REPORT_BYTES}"
            )
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = None
            raw = stream.read(MAX_BENCHMARK_REPORT_BYTES + 1)
    except FileNotFoundError as exc:
        raise RouterBenchmarkError(f"benchmark report not found: {path}") from exc
    except OSError as exc:
        raise RouterBenchmarkError(f"unable to read benchmark report {path}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(raw) > MAX_BENCHMARK_REPORT_BYTES:
        raise RouterBenchmarkError(
            f"benchmark report exceeds {MAX_BENCHMARK_REPORT_BYTES} bytes"
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RouterBenchmarkError(
            f"benchmark report is not valid UTF-8 JSON: {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RouterBenchmarkError("benchmark report root must be a JSON object")
    return payload


def _load_benchmark_split(
    benchmark_path: Path,
    dataset_path: Path,
    dataset: RouterDataset,
) -> tuple[list[int], dict[str, Any], int, float]:
    """Resolve holdout IDs from a file independent of the model artifact."""

    benchmark = _read_benchmark_report(benchmark_path)
    dataset_sha256 = _sha256(dataset_path)
    if benchmark.get("dataset_sha256") != dataset_sha256:
        raise RouterBenchmarkError(
            "benchmark dataset fingerprint does not match the evaluation dataset; "
            "use explicit split overrides to recompute a non-canonical split"
        )
    dataset_total = benchmark.get("dataset_total")
    if isinstance(dataset_total, bool) or not isinstance(dataset_total, int):
        raise RouterBenchmarkError("benchmark dataset_total must be an integer")
    if dataset_total != len(dataset.records):
        raise RouterBenchmarkError("benchmark dataset_total does not match the evaluation dataset")
    test_total = benchmark.get("test_total")
    if isinstance(test_total, bool) or not isinstance(test_total, int) or test_total <= 0:
        raise RouterBenchmarkError("benchmark test_total must be a positive integer")
    holdout_ids = benchmark.get("holdout_record_ids")
    if not isinstance(holdout_ids, list) or len(holdout_ids) != test_total:
        raise RouterBenchmarkError(
            "benchmark holdout_record_ids must contain exactly test_total entries"
        )
    if not all(isinstance(item, str) and 0 < len(item) <= 256 for item in holdout_ids):
        raise RouterBenchmarkError(
            "benchmark holdout record ids must be non-empty strings up to 256 chars"
        )
    if len(set(holdout_ids)) != len(holdout_ids):
        raise RouterBenchmarkError("benchmark holdout record ids must be unique")

    split = benchmark.get("split")
    if not isinstance(split, dict):
        raise RouterBenchmarkError("benchmark split must be a JSON object")
    seed = benchmark.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise RouterBenchmarkError("benchmark seed must be an integer")
    test_size = benchmark.get("test_size")
    if isinstance(test_size, bool) or not isinstance(test_size, (int, float)):
        raise RouterBenchmarkError("benchmark test_size must be numeric")
    if not math.isfinite(float(test_size)) or not 0.0 < float(test_size) < 1.0:
        raise RouterBenchmarkError("benchmark test_size must be between 0 and 1")

    key_to_index = {key: index for index, key in enumerate(_record_keys(dataset))}
    missing_ids = [record_id for record_id in holdout_ids if record_id not in key_to_index]
    if missing_ids:
        raise RouterBenchmarkError(
            f"benchmark holdout cannot be replayed; {len(missing_ids)} record ids are missing"
        )
    return (
        [key_to_index[record_id] for record_id in holdout_ids],
        dict(split),
        seed,
        float(test_size),
    )


def train_model(
    dataset_path: Path = DEFAULT_DATASET,
    artifact_path: Path = DEFAULT_TRAIN_ARTIFACT,
    report_path: Path = DEFAULT_TRAIN_REPORT,
    seed: int = 42,
    test_size: float = 0.2,
    split_group: str | None = "topic",
) -> dict[str, Any]:
    _reject_colliding_training_paths(dataset_path, artifact_path, report_path)
    _require_sklearn("train the learned router")
    dataset = load_dataset(dataset_path)
    labels = sorted(set(dataset.labels))
    if set(labels) != EXPECTED_ROUTER_LABELS:
        raise ValueError(
            "router training labels must exactly match the project label set; "
            f"got {labels}"
        )
    train_idx, test_idx, split_metadata = _split_indices(dataset, test_size, seed, split_group)
    record_keys = _record_keys(dataset)

    train_texts = _subset(dataset.texts, train_idx)
    train_labels = _subset(dataset.labels, train_idx)
    test_texts = _subset(dataset.texts, test_idx)
    test_labels = _subset(dataset.labels, test_idx)
    test_records = _subset(dataset.records, test_idx)

    model = build_model(seed)
    model.fit(train_texts, train_labels)
    sklearn_predictions = list(model.predict(test_texts))

    metadata: dict[str, Any] = {
        "model_type": "tfidf_char_ngram_logistic_regression",
        "dataset": _display_path(dataset_path),
        "dataset_sha256": _sha256(dataset_path),
        "dataset_total": len(dataset.records),
        "labels": labels,
        "seed": seed,
        "test_size": test_size,
        "train_total": len(train_texts),
        "test_total": len(test_texts),
        "holdout_record_ids": _subset(record_keys, test_idx),
        "split": split_metadata,
        "training_dependencies": _dependency_versions(),
        "training_config": {
            "classifier": {
                "C": 4.0,
                "class_weight": "balanced",
                "max_iter": 1000,
                "random_state": seed,
                "solver": "saga",
            },
            "vectorizer": {
                "analyzer": "char",
                "lowercase": True,
                "min_df": 1,
                "ngram_range": [2, 5],
                "sublinear_tf": True,
            },
        },
        "evaluation_scope": "offline synthetic holdout; not evidence of real-user generalization",
    }
    artifact_payload = _portable_payload(model, metadata)
    portable_model, _ = _model_from_payload(artifact_payload)
    portable_predictions = portable_model.predict(test_texts)
    if portable_predictions != sklearn_predictions:
        mismatches = sum(
            portable != sklearn
            for portable, sklearn in zip(portable_predictions, sklearn_predictions)
        )
        raise RouterArtifactError(
            f"portable artifact verification failed: {mismatches} predictions differ from sklearn"
        )

    _write_artifact(artifact_path, artifact_payload)
    metrics = evaluate_predictions(test_labels, portable_predictions, labels, test_records)
    report: dict[str, Any] = {
        **metadata,
        "artifact": {
            "format": ARTIFACT_FORMAT,
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "path": _display_path(artifact_path),
            "sha256": _sha256(artifact_path),
        },
        "metrics": metrics,
        "limitations": [
            "The dataset is synthetic and contains repeated wording patterns.",
            "Offline holdout metrics do not measure downstream learning outcomes.",
            split_metadata.get("limitation", "Group holdout reduces, but does not eliminate, dataset bias."),
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    _atomic_write(report_path, (report_text + "\n").encode("utf-8"))
    return report


def evaluate_model(
    dataset_path: Path = DEFAULT_DATASET,
    artifact_path: Path = DEFAULT_ARTIFACT,
    benchmark_path: Path | None = DEFAULT_REPORT,
    seed: int | None = None,
    test_size: float | None = None,
    split_group: str | None = None,
) -> dict[str, Any]:
    _require_sklearn("evaluate a saved router model")
    model, metadata = load_model(artifact_path)
    dataset = load_dataset(dataset_path)
    labels = sorted(set(dataset.labels))
    if set(labels) != EXPECTED_ROUTER_LABELS:
        raise ValueError(
            "router evaluation labels must exactly match the project label set; "
            f"got {labels}"
        )
    dataset_sha256 = _sha256(dataset_path)
    dataset_matches_training = dataset_sha256 == metadata.get("dataset_sha256")
    use_benchmark = (
        benchmark_path is not None
        and seed is None
        and test_size is None
        and split_group is None
    )
    benchmark_info: dict[str, Any] | None = None
    if use_benchmark:
        test_idx, split_metadata, effective_seed, effective_test_size = _load_benchmark_split(
            benchmark_path,
            dataset_path,
            dataset,
        )
        benchmark_holdout_ids = [_record_keys(dataset)[index] for index in test_idx]
        if metadata.get("holdout_record_ids") != benchmark_holdout_ids:
            raise RouterBenchmarkError(
                "artifact training holdout claim does not match the external benchmark; "
                "refusing a potentially leaked or incomparable evaluation"
            )
        effective_split_group = str(split_metadata.get("group_field", DEFAULT_EVAL_SPLIT_GROUP))
        split_metadata["replayed_from_benchmark"] = True
        split_metadata["artifact_holdout_used"] = False
        split_metadata["artifact_holdout_claim_matches_benchmark"] = True
        benchmark_info = {
            "path": _display_path(benchmark_path),
            "sha256": _sha256(benchmark_path),
        }
    else:
        effective_seed = DEFAULT_EVAL_SEED if seed is None else seed
        effective_test_size = DEFAULT_EVAL_TEST_SIZE if test_size is None else test_size
        effective_split_group = DEFAULT_EVAL_SPLIT_GROUP if split_group is None else split_group
        _, test_idx, split_metadata = _split_indices(
            dataset,
            effective_test_size,
            effective_seed,
            effective_split_group,
        )
        split_metadata["replayed_from_benchmark"] = False
        split_metadata["artifact_holdout_used"] = False
    test_texts = _subset(dataset.texts, test_idx)
    test_labels = _subset(dataset.labels, test_idx)
    test_records = _subset(dataset.records, test_idx)
    predicted = list(model.predict(test_texts))
    return {
        "artifact": str(artifact_path),
        "artifact_sha256": _sha256(artifact_path),
        "dataset": _display_path(dataset_path),
        "dataset_sha256": dataset_sha256,
        "dataset_matches_training": dataset_matches_training,
        "benchmark": benchmark_info,
        "trained_dataset": metadata.get("dataset"),
        "seed": effective_seed,
        "test_size": effective_test_size,
        "split": split_metadata,
        "test_total": len(test_texts),
        "metrics": evaluate_predictions(test_labels, predicted, labels, test_records),
        "evaluation_scope": "offline synthetic holdout; not evidence of real-user generalization",
    }


def load_model(path: Path = DEFAULT_ARTIFACT) -> tuple[PortableRouterModel, dict[str, Any]]:
    """Load and validate a data-only router artifact.

    Pickle/joblib files are intentionally rejected because deserializing them
    can execute arbitrary code and their private NumPy paths are version-bound.
    """

    return _model_from_payload(_read_artifact(path))


def predict(text: str, model_path: Path = DEFAULT_ARTIFACT, top_k: int = 3) -> dict[str, Any]:
    if top_k < 1:
        raise ValueError(f"top_k must be at least 1, got {top_k}")
    model, metadata = load_model(model_path)
    label = model.predict([text])[0]
    result: dict[str, Any] = {
        "text": text,
        "label": label,
        "model": metadata.get("model_type", "unknown"),
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
    }
    probabilities = model.predict_proba([text])[0]
    ranked = sorted(
        zip(model.classes_, probabilities), key=lambda item: item[1], reverse=True
    )[:top_k]
    result["top_k"] = [
        {"label": ranked_label, "probability": float(probability)}
        for ranked_label, probability in ranked
    ]
    return result


def route(
    text: str,
    model_path: Path = DEFAULT_ARTIFACT,
    min_confidence: float = 0.35,
    top_k: int = 3,
) -> dict[str, Any]:
    """Predict with confidence and flag low-confidence cases for fallback."""

    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError(f"min_confidence must be between 0 and 1, got {min_confidence}")
    result = predict(text, model_path=model_path, top_k=top_k)
    top = result["top_k"]
    confidence = top[0]["probability"]
    result["confidence"] = confidence
    result["needs_fallback"] = confidence < min_confidence
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train or run the learned Scientific Learning router.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train_parser = subparsers.add_parser("train", help="train and safely export the router model")
    train_parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    train_parser.add_argument("--artifact", default=str(DEFAULT_TRAIN_ARTIFACT))
    train_parser.add_argument("--report", default=str(DEFAULT_TRAIN_REPORT))
    train_parser.add_argument("--seed", type=int, default=42)
    train_parser.add_argument("--test-size", type=float, default=0.2)
    train_parser.add_argument(
        "--split-group",
        choices=("topic", "subject", "source", "none"),
        default="topic",
        help="hold out groups to reduce train/test leakage (default: topic)",
    )

    predict_parser = subparsers.add_parser("predict", help="predict a route")
    predict_parser.add_argument("text")
    predict_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    predict_parser.add_argument("--top-k", type=int, default=3)
    predict_parser.add_argument("--min-confidence", type=float, default=0.35)

    eval_parser = subparsers.add_parser("evaluate", help="evaluate a saved router model")
    eval_parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    eval_parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    eval_parser.add_argument(
        "--benchmark",
        default=str(DEFAULT_REPORT),
        help="external report containing the frozen holdout IDs (default: checked-in report)",
    )
    eval_parser.add_argument(
        "--recompute-split",
        action="store_true",
        help="ignore the external benchmark and recompute a split from explicit/default options",
    )
    eval_parser.add_argument("--seed", type=int)
    eval_parser.add_argument("--test-size", type=float)
    eval_parser.add_argument(
        "--split-group",
        choices=("topic", "subject", "source", "none"),
        help="override the split group stored in the artifact",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "train":
            report = train_model(
                dataset_path=Path(args.dataset),
                artifact_path=Path(args.artifact),
                report_path=Path(args.report),
                seed=args.seed,
                test_size=args.test_size,
                split_group=args.split_group,
            )
            summary = {
                "artifact": args.artifact,
                "artifact_sha256": report["artifact"]["sha256"],
                "report": args.report,
                "train_total": report["train_total"],
                "test_total": report["test_total"],
                "split": report["split"],
                "accuracy": report["metrics"]["accuracy"],
                "macro_f1": report["metrics"]["macro_f1"],
                "hard_negative": report["metrics"].get("hard_negative"),
                "non_learning": report["metrics"].get("non_learning"),
                "evaluation_scope": report["evaluation_scope"],
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        if args.command == "evaluate":
            report = evaluate_model(
                dataset_path=Path(args.dataset),
                artifact_path=Path(args.artifact),
                benchmark_path=None if args.recompute_split else Path(args.benchmark),
                seed=args.seed,
                test_size=args.test_size,
                split_group=args.split_group,
            )
            summary = {
                "artifact": report["artifact"],
                "artifact_sha256": report["artifact_sha256"],
                "dataset": report["dataset"],
                "dataset_matches_training": report["dataset_matches_training"],
                "benchmark": report["benchmark"],
                "test_total": report["test_total"],
                "split": report["split"],
                "accuracy": report["metrics"]["accuracy"],
                "macro_f1": report["metrics"]["macro_f1"],
                "hard_negative": report["metrics"].get("hard_negative"),
                "non_learning": report["metrics"].get("non_learning"),
                "evaluation_scope": report["evaluation_scope"],
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        result = route(
            args.text,
            model_path=Path(args.artifact),
            min_confidence=args.min_confidence,
            top_k=args.top_k,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (FileNotFoundError, MLDependencyError, RouterArtifactError, ValueError) as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover - argparse exits


if __name__ == "__main__":
    raise SystemExit(main())
