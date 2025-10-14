# PyTorch & ONNX Migration Blueprint

Migrating DocReview360's critics from FANN to PyTorch + ONNX Runtime requires a coordinated delivery plan that spans model development, product integration, automated testing, and documentation. This blueprint captures every workstream defined in the migration recommendation and maps them to concrete engineering tasks, validation criteria, and doc updates.

## How to use this document

1. Use the task lists as backlog items for implementation teams.
2. Treat the testing coverage bullets as acceptance criteria for code review.
3. Mirror the documentation updates in the docs portal and release notes.
4. Keep this file in sync with `docreview360.ml.pytorch_migration_plan` so the automated tests continue to verify completeness.

## Model replacements

### Document quality & style critic

**Summary**: Replace the existing heuristic/FANN quality critic with a PyTorch MLP exported to ONNX that scores readability, structure, and editorial risk.

**Implementation tasks**
- Design deterministic feature vector covering readability deltas, heading density, section length ratios, passive-voice percentage, and table/figure coverage.
- Implement PyTorch model definition and training pipeline that can run locally without CUDA.
- Export trained weights to ONNX and register the artifact with model version metadata.
- Wire ONNX Runtime inference into the FastAPI critic service and replace the legacy FANN scorer.

**Testing coverage**
- Golden fixture test validating deterministic feature extraction and score stability across releases.
- Unit test ensuring ONNX inference outputs score within acceptable delta compared to native PyTorch evaluation for sample docs.
- Integration test covering FastAPI `/ml/score-quality` endpoint with editorial flag assertions.

**Documentation updates**
- Update quality critic section in ML operations guide to describe PyTorch architecture and export workflow.
- Add CLI usage example demonstrating `docreview360 validate --ml` with quality critic output.

### Template compliance classifier

**Summary**: Train a PyTorch MLP that evaluates template compliance using parser features and outputs probabilities for enforcement policies.

**Implementation tasks**
- Align parser-derived compliance signals with versioned JSON schema in `docs/ml/compliance_features.schema.json`.
- Develop training dataset with labeled compliance outcomes and train MLP baseline in PyTorch.
- Export classifier to ONNX and publish calibration thresholds for workflow guards.
- Integrate ONNX inference into guardrails pipeline replacing FANN logic.

**Testing coverage**
- Schema contract test verifying inference payloads conform to compliance feature schema.
- Model regression test asserting probability outputs remain within tolerance for key compliance fixtures.
- End-to-end guardrail test blocking export when compliance score falls below threshold.

**Documentation updates**
- Document compliance model features and calibration guidance in the compliance documentation set.
- Add troubleshooting section for low-confidence compliance results and escalation steps.

### Reviewer routing & approval likelihood

**Summary**: Deliver PyTorch routing model that recommends reviewers and predicts approval latency to support workload balancing.

**Implementation tasks**
- Consolidate routing features (doc type, size, historical reviewer data, workload indicators) into shared schema.
- Prototype gradient-boosted baseline, then implement PyTorch MLP for production parity.
- Export ONNX model supporting top-k reviewer recommendations and latency buckets.
- Connect routing predictions to reviewer assignment automation and dashboard visualizations.

**Testing coverage**
- Compare PyTorch predictions against scikit-learn baseline to ensure performance parity or better.
- Unit test verifying deterministic top-k reviewer ordering for known fixtures.
- Integration test covering `/ml/route-reviewer` endpoint with simulated workloads.

**Documentation updates**
- Extend reviewer operations guide with routing score interpretation and dashboard widgets.
- Document CLI workflow for `docreview360 ml-benchmark` comparing baseline and PyTorch models.

### Signature anomaly scoring

**Summary**: Introduce PyTorch anomaly detector scoring signature metadata to trigger verification escalations.

**Implementation tasks**
- Define signature feature schema covering provider metadata, verification timing, certificate attributes, and retry behavior.
- Train anomaly detection network (e.g., autoencoder) tuned for low false positives on signature events.
- Export ONNX model and integrate with signature verification flow.
- Implement escalation hooks mapping anomaly score to policy actions.

**Testing coverage**
- Replay historical signature anomalies to ensure high recall.
- Unit test confirming deterministic feature encoding for provider metadata.
- Integration test covering `/ml/score-signature` endpoint and policy escalation trigger.

**Documentation updates**
- Update signature verification runbook with anomaly score response procedures.
- Add dashboard annotation examples illustrating anomaly distribution and alerting thresholds.

## Platform capabilities

### Model shim & export pipeline

**Summary**: Create reusable PyTorch helper layer that standardizes training, ONNX export, and metadata logging for all critics.

**Implementation tasks**
- Implement `docreview360/ml/torch_models.py` with reusable modules for critic networks.
- Add `docreview360/ml/onnx_infer.py` providing lazy ONNX Runtime session loading and input validation.
- Ensure model artifacts log git SHA, dataset version, and export hash.
- Provide quantization utilities for optional INT8 exports.

**Testing coverage**
- Unit tests covering ONNX loader error handling and caching logic.
- Snapshot tests verifying exported model metadata payloads.
- Quantization regression ensuring INT8 exports stay within accuracy tolerance.

**Documentation updates**
- Add developer guide outlining training → export workflow and metadata requirements.
- Document quantization trade-offs and usage instructions.

### Feature adapters

**Summary**: Harden feature extraction adapters that convert existing parsing signals into model-ready tensors.

**Implementation tasks**
- Version feature schemas and align adapters with JSON schema definitions.
- Implement deterministic ordering and normalization for all feature vectors.
- Add spaCy and RapidFuzz optional accelerators with graceful fallback.
- Expose adapters through CLI for offline inspection and validation.

**Testing coverage**
- Schema validation test ensuring adapters emit values that conform to the published JSON schemas.
- Property-based test confirming idempotent feature extraction for the same source document.
- Performance benchmark test verifying adapter latency budget.

**Documentation updates**
- Document feature vector schemas in docs/ml with examples.
- Provide troubleshooting matrix for adapter failures and optional dependency installation.

### FastAPI serving endpoints

**Summary**: Expose ML critics through FastAPI endpoints that reuse ONNX Runtime sessions and follow existing auth patterns.

**Implementation tasks**
- Register `/ml/score-quality`, `/ml/route-reviewer`, and `/ml/score-signature` endpoints.
- Load ONNX sessions during FastAPI startup and reuse them per request.
- Implement request/response schemas and validation errors.
- Integrate observability hooks (metrics and structured logs).

**Testing coverage**
- API contract tests validating response schema and HTTP status codes.
- Load test ensuring cold-start and steady-state latency targets.
- AuthZ test confirming only permitted roles can access ML endpoints.

**Documentation updates**
- Update API reference with endpoint details, parameters, and examples.
- Add runbook entries for redeploying models without restarting the application server.

### Dashboards & analytics integration

**Summary**: Surface model scores in dashboard feeds, CSV exports, and websocket streams for monitoring.

**Implementation tasks**
- Extend metrics pipeline to include critic outputs and model version tags.
- Backfill historical dashboards with new metrics when available.
- Update CSV export and websocket payloads to carry ML scores.
- Add anomaly alerts based on score thresholds.

**Testing coverage**
- Unit test verifying metrics payload includes all new fields.
- Regression test for CSV exporter to ensure column order stability.
- Dashboard UI test confirming new visualizations render correctly.

**Documentation updates**
- Update analytics documentation with descriptions of new ML metrics.
- Provide dashboard configuration examples highlighting score widgets.

### Guardrails & workflow policies

**Summary**: Map ML critic scores to workflow actions that block risky publishes and auto-assign reviewers.

**Implementation tasks**
- Define policy thresholds for each critic (quality, compliance, routing, signature).
- Integrate thresholds with existing guardrail middleware and event notifications.
- Implement override/audit logging when policies are bypassed.
- Ensure escalation paths align with security and compliance mandates.

**Testing coverage**
- Unit test verifying guardrail middleware triggers actions at the correct score thresholds.
- Audit log test confirming overrides capture ML context.
- End-to-end workflow test covering publish attempt blocked by critic.

**Documentation updates**
- Document policy mapping matrix linking scores to actions.
- Update compliance and security runbooks with escalation workflow steps.

### CLI tooling

**Summary**: Extend DocReview360 CLI with training, benchmarking, and validation commands for the new ML stack.

**Implementation tasks**
- Implement `docreview360 ml-train` to orchestrate PyTorch training and ONNX export.
- Add `docreview360 ml-benchmark` for baseline comparisons.
- Update `docreview360 validate --ml` to display critic outputs next to rule-based checks.
- Provide offline evaluation command for schema validation.

**Testing coverage**
- CLI invocation tests using click/typer runner verifying command signatures and output structure.
- Integration test ensuring CLI can load exported ONNX models.
- Snapshot test of benchmark report formatting.

**Documentation updates**
- Update CLI reference with new commands and options.
- Add quickstart tutorial covering local training and benchmarking.

### Testing & operational readiness

**Summary**: Institutionalize tests, monitoring, and audit logging for the ML critics to maintain long-term reliability.

**Implementation tasks**
- Automate golden-fixture regression tests in CI.
- Emit model version, ONNX hash, and quantization status in audit logs.
- Schedule periodic retraining checks with data drift reports.
- Document rollback procedure for reverting to previous model exports.

**Testing coverage**
- CI pipeline step verifying golden tests execute on pull requests.
- Operational test ensuring audit logs capture model metadata fields.
- Drift detection test comparing recent performance metrics to baseline.

**Documentation updates**
- Update operations playbook with retraining cadence and rollback plan.
- Add section to security documentation covering audit log contents.

### Optional helper libraries

**Summary**: Track adoption of spaCy, RapidFuzz, and quantization to improve feature quality and inference efficiency.

**Implementation tasks**
- Evaluate spaCy integration for entity-based compliance signals and document installation process.
- Benchmark RapidFuzz for duplicate detection during routing.
- Prototype INT8 quantization path for critical models and measure latency improvements.
- Create feature flags toggling helper usage at runtime.

**Testing coverage**
- Performance benchmarks comparing helper-enabled vs fallback paths.
- Feature-flag unit tests ensuring graceful degradation when helpers are unavailable.
- Quantized model accuracy regression tests.

**Documentation updates**
- Update dependency notes for optional helpers including Apple Silicon support considerations.
- Add FAQ addressing when to enable helpers and expected benefits.

## Operational checklist

Run these commands before shipping any critic update:

```bash
pytest tests/ml/test_pytorch_migration_plan.py
docreview360 ml test --suite golden
docreview360 ml eval --baseline scikit
```

Record the exported ONNX hash, feature schema version, and quantization status in the deployment log after each rollout.
