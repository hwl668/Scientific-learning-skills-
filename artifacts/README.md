# Router model artifact

`learning_agent/resources/artifacts/router_model_v0.3.json.gz` is the checked-in baseline for routing a short
learning request to one of the project's learning modes. It is a versioned,
data-only JSON artifact compressed with gzip (schema version 2). The loader validates its schema,
dimensions, numeric values, and size; it deliberately refuses pickle, joblib,
and other executable serialization formats.

## Intended use

- Reproduce the repository's learned-router demo and offline evaluation.
- Provide top-k route suggestions and a confidence signal to a caller that can
  ask a clarification question or fall back to deterministic routing.
- Serve as a lightweight baseline for comparing future routing approaches.

It is not intended to grade students, make high-stakes educational decisions,
or run as an autonomous tutor without a fallback and human-visible behavior.

## Training and split

- Dataset: `learning_agent/resources/data/training/router_training_v0.3.jsonl`
- Dataset SHA-256:
  `8c4bbc6efce6face1e16ad7ce7ca05bfe32aa4e99800f9b05d6a4f791d41cd09`
- Model: character 2-5 gram TF-IDF + balanced logistic regression
- Seed: `42`
- Split: balanced topic-group holdout where possible, 1,788 train / 443 test
- Artifact SHA-256:
  `ef8d6c2a235f8f4a161ebc2e30188ea170f5300aa4c6cea43009b8ac9bed3096`

The `non-learning` label has only one raw topic group. Its records therefore
use stable record-ID groups so that the class remains present in both
partitions. The report records this fallback and the remaining raw-topic
overlap; this benchmark must not be described as fully group-disjoint.
The checked-in report stores the 443 frozen holdout record IDs independently
of the model being evaluated. Default evaluation reads that report, uses it as
the only row-selection source, and rejects an artifact whose training-split
claim differs from it. The artifact copy is a consistency check, not a way for
the candidate model to select favorable rows. The report is still
repository-authored benchmark data, not an external or adversary-proof test set.

The exact metrics, split diagnostics, configuration, dependency versions, and
limitations are machine-readable in
`learning_agent/resources/artifacts/router_model_v0.3_report.json`.
Routine `train` commands write to `artifacts/generated/`; the trainer refuses
to overwrite the checked-in artifact or frozen benchmark report. Promotion of
a newly reviewed baseline is therefore an explicit maintainer action.

## Training environment

| Dependency | Recorded version |
|---|---:|
| Python | 3.10.1 |
| NumPy | 1.23.5 |
| SciPy | 1.10.1 |
| scikit-learn | 1.7.2 |

These versions document provenance, not an inference requirement. Prediction
uses the repository's pure-Python artifact reader. Training and metric
evaluation require the `ml` optional dependency.

## Limitations

- The training set is synthetic and repeats wording patterns.
- Offline holdout scores do not establish generalization to real learners.
- Routing accuracy does not measure whether a learner understood, retained, or
  transferred knowledge. This artifact provides no evidence of learning effect.
- Confidence values are model probabilities, not a validated safety guarantee.

The legacy `router_model_v0.3.pkl` was removed from the working tree. It remains
available in Git history for provenance only and must not be loaded: pickle can
execute arbitrary code and depends on private NumPy/scikit-learn module paths.
Retrain to the JSON.GZ format instead.
