import pytest
from docreview360.celery_app import quality_gate
from docreview360.documents import DocumentModel
from docreview360.exporter import (
    export_document,
    get_guardrails_diagnostics,
    set_guardrails,
)
from docreview360.guardrails import GuardrailThresholds
from docreview360.wasm_plugin import lint_text


@pytest.fixture(autouse=True)
def _fake_guardrail_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide deterministic critic outputs for guardrail tests."""

    from docreview360.ml.compliance_classifier import ComplianceClassification
    from docreview360.quality import QualityAssessment

    def fake_quality(text: str, doc_type: str | None = None) -> QualityAssessment:
        lower = text.lower()
        if "urgent" in lower:
            return QualityAssessment(score=0.6, raw_score=0.6, flags=(0.9, 0.2, 0.1))
        if "review" in lower:
            return QualityAssessment(score=0.82, raw_score=0.82, flags=(0.2, 0.2, 0.2))
        return QualityAssessment(score=0.92, raw_score=0.92, flags=(0.1, 0.1, 0.1))

    def fake_compliance(
        text: str, metadata: dict[str, object] | None = None
    ) -> ComplianceClassification:
        lower = text.lower()
        if "urgent" in lower:
            return ComplianceClassification(
                probability=0.4,
                failing_rules=["high_risk"],
                features={},
                source="onnx",
            )
        return ComplianceClassification(
            probability=0.72,
            failing_rules=[],
            features={},
            source="onnx",
        )

    monkeypatch.setattr("docreview360.guardrails.quality_assessment", fake_quality)
    monkeypatch.setattr("docreview360.guardrails.evaluate_compliance", fake_compliance)


@pytest.fixture
def policy_thresholds(monkeypatch: pytest.MonkeyPatch) -> GuardrailThresholds:
    thresholds = GuardrailThresholds(
        min_quality_score=0.75,
        quality_flag_threshold=0.8,
        min_compliance_probability=0.5,
        auto_assign_editor="qa-team",
        auto_assign_quality_below=0.85,
    )

    def loader() -> GuardrailThresholds:
        return thresholds

    monkeypatch.setattr("docreview360.guardrails.load_guardrail_thresholds", loader)
    monkeypatch.setattr("docreview360.celery_app.load_guardrail_thresholds", loader)
    monkeypatch.setattr("docreview360.wasm_plugin.load_guardrail_thresholds", loader)
    monkeypatch.setattr("docreview360.ai_utils.load_guardrail_thresholds", loader)
    return thresholds


def test_guardrail_failure_blocks_export(
    monkeypatch: pytest.MonkeyPatch, policy_thresholds: GuardrailThresholds
) -> None:
    monkeypatch.setattr("docreview360.exporter.guardrails_checker", None)
    monkeypatch.setattr("docreview360.exporter.guardrail_thresholds", None)
    monkeypatch.setattr("docreview360.exporter.guardrails_diagnostics", None)

    set_guardrails(None, thresholds=policy_thresholds)

    failing = DocumentModel(id="doc-urgent", content="URGENT incident requires action", history=[])
    with pytest.raises(ValueError, match="guardrails"):
        export_document(failing, "markdown")

    diag = get_guardrails_diagnostics()
    assert diag is not None
    assert diag["blocked"] is True
    assert diag["passed"] is False
    assert diag["thresholds"]["min_quality_score"] == policy_thresholds.min_quality_score

    borderline = DocumentModel(id="doc-review", content="Needs review by editor", history=[])
    data, media, name = export_document(borderline, "markdown")
    assert media == "text/markdown"
    assert name.endswith(".md")
    assert data

    diag = get_guardrails_diagnostics()
    assert diag is not None
    assert diag["blocked"] is False
    assert diag["auto_assign_editor"] == policy_thresholds.auto_assign_editor


def test_guardrail_thresholds_used_by_tasks(policy_thresholds: GuardrailThresholds) -> None:
    bad_result = quality_gate("URGENT escalation")
    assert bad_result["blocked"] is True
    assert bad_result["thresholds"]["min_quality_score"] == policy_thresholds.min_quality_score

    good_result = quality_gate("Team update ready for publication")
    assert good_result["blocked"] is False
    assert lint_text("Team update ready for publication") is True
    assert lint_text("URGENT escalation") is False
