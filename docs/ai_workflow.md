# AI in the DocReview360 Workflow

DocReview360 pairs a compact PyTorch classifier with ONNX Runtime so document
triage remains fast without depending on cloud inference. This guide explains
how we train, export, validate, and run the model across environments.

## PyTorch → ONNX pipeline

1. **Train in PyTorch.**
   Run `docreview360 ml train` to fine-tune the review classifier. The command
   loads features described in `schemas/features.json`, stores checkpoints in
   `artifacts/models/`, and records metrics in `artifacts/metrics/latest.json`.
2. **Freeze and export.**
   Execute `docreview360 ml export --opset 18` to convert the most recent
   `latest.pt` checkpoint to `latest.onnx`. The exporter preserves dynamic axes
   for variable-length inputs and embeds metadata fields such as
   `docreview360:feature_schema` so inference servers can validate payloads.
3. **Optional quantization.**
   Append `--quantize dynamic` (quick INT8 pass) or `--quantize static` with a
   calibration set to generate CPU-optimized graphs. The exporter stores
   floating-point and quantized models side by side to simplify A/B testing.
4. **Package for deployment.**
   `docreview360 ml package` copies the ONNX graph, tokenizer assets, and
   feature schema into a timestamped directory under `artifacts/packages/`.

## CPU-friendly inference

In production the API workers load the packaged ONNX model with:

```bash
DOCREVIEW360_ML_MODEL_DIR=/app/artifacts/packages/2024-05-01_120000 \
DOCREVIEW360_ML_PROVIDER=cpu \
DOCREVIEW360_ML_THREADS=4 \
uvicorn docreview360.api:app
```

The runtime requests `CPUExecutionProvider` first, then falls back to
`CoreMLExecutionProvider` (Apple Silicon) and `OpenVINOExecutionProvider` when
available. If none of the providers load, the worker logs an actionable error—
see the troubleshooting section in `docs/deployment.md`.

## Testing the exported graph

We rely on three guardrails before promoting a model:

1. **Golden tests** replay a curated set of documents via
   `docreview360 ml test --suite golden`, asserting top-1 labels and score
   deltas stay within tolerance.
2. **Baseline comparison** runs `docreview360 ml eval --baseline scikit` to
   compare the ONNX model against a scikit-learn reference trained on the same
   features. The CLI prints accuracy, precision/recall, and ROC AUC deltas.
3. **Schema verification** uses `docreview360 ml schema validate` to ensure the
   `feature_schema.json` shipped with the package matches the model metadata.

## Optional language helpers

Teams that enable spaCy or RapidFuzz get extra signals during feature
generation:

- `pip install "spacy>=3.7"` to unlock entity extraction features referenced in
  `schemas/features.json`.
- `pip install rapidfuzz` to improve duplicate-check heuristics that feed the
  anomaly score.

Both dependencies are optional—the CLI automatically disables the matching
features when the libraries are missing.
