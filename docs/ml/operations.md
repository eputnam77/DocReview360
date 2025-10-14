# ML Operations Playbook

Keeping the DocReview360 model healthy requires a lightweight but repeatable
process. This playbook covers the feature schema contract, automated tests,
baseline comparisons, and optional helpers that improve feature engineering.

## Feature schemas

DocReview360 describes every input vector with a JSON schema stored in
`docs/ml/*_features.schema.json`. Each schema aligns with a `.sample.json` file
that demonstrates valid payloads. When you change features:

1. Update the relevant schema to capture new fields or constraints.
2. Regenerate the sample file so other teams can test against realistic data.
3. Run `docreview360 ml schema validate --path docs/ml/` to confirm the ONNX
   metadata matches the schema definition.

> **Tip:** Schema diffs are part of code review. They prevent silent breaking
> changes between the training and inference pipelines.

## Golden tests

Golden tests replay curated documents through the model and assert outputs stay
within tolerance. Trigger them locally with:

```bash
docreview360 ml test --suite golden
```

The suite compares predicted labels, confidence scores, and explanation tokens.
If a value drifts beyond the allowed delta the command prints a diff so you can
inspect the regression. Add new golden samples whenever you expand the feature
schema or observe a new document pattern in production.

## Baseline comparisons

Before shipping a new model run:

```bash
docreview360 ml eval --baseline scikit
```

The CLI fits a scikit-learn baseline (logistic regression by default) using the
same feature schema. It outputs a table with accuracy, precision/recall, ROC AUC,
and macro-F1 scores. If the ONNX model underperforms the baseline, pause the
rollout and investigate training data drift or feature bugs.

## Optional helpers

Two optional libraries improve feature extraction:

- **spaCy** – enables entity-based signals that boost compliance scoring. Install
  with `pip install "spacy>=3.7"` and download the language model referenced in
  `schemas/features.json`.
- **RapidFuzz** – accelerates fuzzy matching used for duplicate detection during
  routing. Add it via `pip install rapidfuzz`.

Both helpers are auto-detected. When they are missing the CLI falls back to
pure-Python implementations so you can still train and export models in
restricted environments.
