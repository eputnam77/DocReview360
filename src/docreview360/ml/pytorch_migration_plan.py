"""Structured migration plan for replacing FANN with PyTorch and ONNX Runtime.

This module captures the actionable tasks, test coverage, and documentation
responsibilities required to ship the migration described in the PyTorch/ONNX
recommendation memo.  The data is intentionally verbose so it can be consumed by
CLI helpers, documentation generators, or future automations without the need to
re-parse free-form Markdown.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class Workstream:
    """Represents a cohesive unit of work for the PyTorch migration."""

    key: str
    title: str
    summary: str
    tasks: List[str]
    tests: List[str]
    documentation: List[str]


def _workstreams() -> Iterable[Workstream]:
    """Yield the canonical workstreams for the migration."""

    yield Workstream(
        key="quality_critic_model",
        title="Document quality & style critic",
        summary=(
            "Replace the existing heuristic/FANN quality critic with a PyTorch "
            "MLP exported to ONNX that scores readability, structure, and "
            "editorial risk."
        ),
        tasks=[
            "Design deterministic feature vector covering readability deltas, "
            "heading density, section length ratios, passive-voice percentage, "
            "and table/figure coverage.",
            "Implement PyTorch model definition and training pipeline that can "
            "run locally without CUDA.",
            "Export trained weights to ONNX and register the artifact with model "
            "version metadata.",
            "Wire ONNX Runtime inference into the FastAPI critic service and "
            "replace the legacy FANN scorer.",
        ],
        tests=[
            "Golden fixture test validating deterministic feature extraction and "
            "score stability across releases.",
            "Unit test ensuring ONNX inference outputs score within acceptable "
            "delta compared to native PyTorch evaluation for sample docs.",
            "Integration test covering FastAPI `/ml/score-quality` endpoint with "
            "editorial flag assertions.",
        ],
        documentation=[
            "Update quality critic section in ML operations guide to describe "
            "PyTorch architecture and export workflow.",
            "Add CLI usage example demonstrating `docreview360 validate --ml` "
            "with quality critic output.",
        ],
    )

    yield Workstream(
        key="template_compliance_classifier",
        title="Template compliance classifier",
        summary=(
            "Train a PyTorch MLP that evaluates template compliance using parser "
            "features and outputs probabilities for enforcement policies."
        ),
        tasks=[
            "Align parser-derived compliance signals with versioned JSON schema "
            "in `docs/ml/compliance_features.schema.json`.",
            "Develop training dataset with labeled compliance outcomes and train "
            "MLP baseline in PyTorch.",
            "Export classifier to ONNX and publish calibration thresholds for "
            "workflow guards.",
            "Integrate ONNX inference into guardrails pipeline replacing FANN "
            "logic.",
        ],
        tests=[
            "Schema contract test verifying inference payloads conform to "
            "compliance feature schema.",
            "Model regression test asserting probability outputs remain within "
            "tolerance for key compliance fixtures.",
            "End-to-end guardrail test blocking export when compliance score "
            "falls below threshold.",
        ],
        documentation=[
            "Document compliance model features and calibration guidance in the "
            "compliance documentation set.",
            "Add troubleshooting section for low-confidence compliance results "
            "and escalation steps.",
        ],
    )

    yield Workstream(
        key="reviewer_routing_model",
        title="Reviewer routing & approval likelihood",
        summary=(
            "Deliver PyTorch routing model that recommends reviewers and "
            "predicts approval latency to support workload balancing."
        ),
        tasks=[
            "Consolidate routing features (doc type, size, historical reviewer "
            "data, workload indicators) into shared schema.",
            "Prototype gradient-boosted baseline, then implement PyTorch MLP for "
            "production parity.",
            "Export ONNX model supporting top-k reviewer recommendations and "
            "latency buckets.",
            "Connect routing predictions to reviewer assignment automation and "
            "dashboard visualizations.",
        ],
        tests=[
            "Compare PyTorch predictions against scikit-learn baseline to ensure "
            "performance parity or better.",
            "Unit test verifying deterministic top-k reviewer ordering for known "
            "fixtures.",
            "Integration test covering `/ml/route-reviewer` endpoint with "
            "simulated workloads.",
        ],
        documentation=[
            "Extend reviewer operations guide with routing score interpretation "
            "and dashboard widgets.",
            "Document CLI workflow for `docreview360 ml-benchmark` comparing "
            "baseline and PyTorch models.",
        ],
    )

    yield Workstream(
        key="signature_anomaly_model",
        title="Signature anomaly scoring",
        summary=(
            "Introduce PyTorch anomaly detector scoring signature metadata to "
            "trigger verification escalations."
        ),
        tasks=[
            "Define signature feature schema covering provider metadata, "
            "verification timing, certificate attributes, and retry behavior.",
            "Train anomaly detection network (e.g., autoencoder) tuned for low "
            "false positives on signature events.",
            "Export ONNX model and integrate with signature verification flow.",
            "Implement escalation hooks mapping anomaly score to policy actions.",
        ],
        tests=[
            "Replay historical signature anomalies to ensure high recall.",
            "Unit test confirming deterministic feature encoding for provider "
            "metadata.",
            "Integration test covering `/ml/score-signature` endpoint and policy "
            "escalation trigger.",
        ],
        documentation=[
            "Update signature verification runbook with anomaly score response "
            "procedures.",
            "Add dashboard annotation examples illustrating anomaly distribution "
            "and alerting thresholds.",
        ],
    )

    yield Workstream(
        key="model_shim",
        title="Model shim & export pipeline",
        summary=(
            "Create reusable PyTorch helper layer that standardizes training, "
            "ONNX export, and metadata logging for all critics."
        ),
        tasks=[
            "Implement `docreview360/ml/torch_models.py` with reusable modules "
            "for critic networks.",
            "Add `docreview360/ml/onnx_infer.py` providing lazy ONNX Runtime "
            "session loading and input validation.",
            "Ensure model artifacts log git SHA, dataset version, and export hash.",
            "Provide quantization utilities for optional INT8 exports.",
        ],
        tests=[
            "Unit tests covering ONNX loader error handling and caching logic.",
            "Snapshot tests verifying exported model metadata payloads.",
            "Quantization regression ensuring INT8 exports stay within accuracy "
            "tolerance.",
        ],
        documentation=[
            "Add developer guide outlining training → export workflow and "
            "metadata requirements.",
            "Document quantization trade-offs and usage instructions.",
        ],
    )

    yield Workstream(
        key="feature_adapters",
        title="Feature adapters",
        summary=(
            "Harden feature extraction adapters that convert existing parsing "
            "signals into model-ready tensors."
        ),
        tasks=[
            "Version feature schemas and align adapters with JSON schema "
            "definitions.",
            "Implement deterministic ordering and normalization for all feature "
            "vectors.",
            "Add spaCy and RapidFuzz optional accelerators with graceful fallback.",
            "Expose adapters through CLI for offline inspection and validation.",
        ],
        tests=[
            "Schema validation test ensuring adapters emit values that conform "
            "to the published JSON schemas.",
            "Property-based test confirming idempotent feature extraction for the "
            "same source document.",
            "Performance benchmark test verifying adapter latency budget.",
        ],
        documentation=[
            "Document feature vector schemas in docs/ml with examples.",
            "Provide troubleshooting matrix for adapter failures and optional "
            "dependency installation.",
        ],
    )

    yield Workstream(
        key="serving_endpoints",
        title="FastAPI serving endpoints",
        summary=(
            "Expose ML critics through FastAPI endpoints that reuse ONNX Runtime "
            "sessions and follow existing auth patterns."
        ),
        tasks=[
            "Register `/ml/score-quality`, `/ml/route-reviewer`, and "
            "`/ml/score-signature` endpoints.",
            "Load ONNX sessions during FastAPI startup and reuse them per request.",
            "Implement request/response schemas and validation errors.",
            "Integrate observability hooks (metrics and structured logs).",
        ],
        tests=[
            "API contract tests validating response schema and HTTP status codes.",
            "Load test ensuring cold-start and steady-state latency targets.",
            "AuthZ test confirming only permitted roles can access ML endpoints.",
        ],
        documentation=[
            "Update API reference with endpoint details, parameters, and examples.",
            "Add runbook entries for redeploying models without restarting the "
            "application server.",
        ],
    )

    yield Workstream(
        key="dashboards_analytics",
        title="Dashboards & analytics integration",
        summary=(
            "Surface model scores in dashboard feeds, CSV exports, and websocket "
            "streams for monitoring."
        ),
        tasks=[
            "Extend metrics pipeline to include critic outputs and model version "
            "tags.",
            "Backfill historical dashboards with new metrics when available.",
            "Update CSV export and websocket payloads to carry ML scores.",
            "Add anomaly alerts based on score thresholds.",
        ],
        tests=[
            "Unit test verifying metrics payload includes all new fields.",
            "Regression test for CSV exporter to ensure column order stability.",
            "Dashboard UI test confirming new visualizations render correctly.",
        ],
        documentation=[
            "Update analytics documentation with descriptions of new ML metrics.",
            "Provide dashboard configuration examples highlighting score widgets.",
        ],
    )

    yield Workstream(
        key="guardrails_middleware",
        title="Guardrails & workflow policies",
        summary=(
            "Map ML critic scores to workflow actions that block risky publishes "
            "and auto-assign reviewers."
        ),
        tasks=[
            "Define policy thresholds for each critic (quality, compliance, "
            "routing, signature).",
            "Integrate thresholds with existing guardrail middleware and event "
            "notifications.",
            "Implement override/audit logging when policies are bypassed.",
            "Ensure escalation paths align with security and compliance mandates.",
        ],
        tests=[
            "Unit test verifying guardrail middleware triggers actions at the "
            "correct score thresholds.",
            "Audit log test confirming overrides capture ML context.",
            "End-to-end workflow test covering publish attempt blocked by critic.",
        ],
        documentation=[
            "Document policy mapping matrix linking scores to actions.",
            "Update compliance and security runbooks with escalation workflow "
            "steps.",
        ],
    )

    yield Workstream(
        key="cli_tooling",
        title="CLI tooling",
        summary=(
            "Extend DocReview360 CLI with training, benchmarking, and validation "
            "commands for the new ML stack."
        ),
        tasks=[
            "Implement `docreview360 ml-train` to orchestrate PyTorch training "
            "and ONNX export.",
            "Add `docreview360 ml-benchmark` for baseline comparisons.",
            "Update `docreview360 validate --ml` to display critic outputs next to "
            "rule-based checks.",
            "Provide offline evaluation command for schema validation.",
        ],
        tests=[
            "CLI invocation tests using click/typer runner verifying command "
            "signatures and output structure.",
            "Integration test ensuring CLI can load exported ONNX models.",
            "Snapshot test of benchmark report formatting.",
        ],
        documentation=[
            "Update CLI reference with new commands and options.",
            "Add quickstart tutorial covering local training and benchmarking.",
        ],
    )

    yield Workstream(
        key="testing_operations",
        title="Testing & operational readiness",
        summary=(
            "Institutionalize tests, monitoring, and audit logging for the ML "
            "critics to maintain long-term reliability."
        ),
        tasks=[
            "Automate golden-fixture regression tests in CI.",
            "Emit model version, ONNX hash, and quantization status in audit logs.",
            "Schedule periodic retraining checks with data drift reports.",
            "Document rollback procedure for reverting to previous model exports.",
        ],
        tests=[
            "CI pipeline step verifying golden tests execute on pull requests.",
            "Operational test ensuring audit logs capture model metadata fields.",
            "Drift detection test comparing recent performance metrics to baseline.",
        ],
        documentation=[
            "Update operations playbook with retraining cadence and rollback plan.",
            "Add section to security documentation covering audit log contents.",
        ],
    )

    yield Workstream(
        key="optional_helpers",
        title="Optional helper libraries",
        summary=(
            "Track adoption of spaCy, RapidFuzz, and quantization to improve "
            "feature quality and inference efficiency."
        ),
        tasks=[
            "Evaluate spaCy integration for entity-based compliance signals and "
            "document installation process.",
            "Benchmark RapidFuzz for duplicate detection during routing.",
            "Prototype INT8 quantization path for critical models and measure "
            "latency improvements.",
            "Create feature flags toggling helper usage at runtime.",
        ],
        tests=[
            "Performance benchmarks comparing helper-enabled vs fallback paths.",
            "Feature-flag unit tests ensuring graceful degradation when helpers "
            "are unavailable.",
            "Quantized model accuracy regression tests.",
        ],
        documentation=[
            "Update dependency notes for optional helpers including Apple Silicon "
            "support considerations.",
            "Add FAQ addressing when to enable helpers and expected benefits.",
        ],
    )


WORKSTREAMS: Dict[str, Workstream] = {ws.key: ws for ws in _workstreams()}


def get_workstreams() -> Dict[str, Workstream]:
    """Return an immutable mapping of workstream key to configuration."""

    return dict(WORKSTREAMS)


__all__ = ["Workstream", "WORKSTREAMS", "get_workstreams"]
