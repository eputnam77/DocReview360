import json
from pathlib import Path

import pytest

from docreview360 import approvals, quality as quality_module
from docreview360.quality import (
    QUALITY_FLAG_NAMES,
    explain_score,
    quality_assessment,
    quality_model_metadata,
)

_FIXTURE_PATH = Path(__file__).resolve().parent / "data" / "ml" / "quality.json"
_QUALITY_FIXTURE = json.loads(_FIXTURE_PATH.read_text())


def _golden_assessment() -> dict[str, object]:
    return _QUALITY_FIXTURE["assessment"]  # type: ignore[index]


def _golden_input_text() -> str:
    return _QUALITY_FIXTURE["input"]["text"]  # type: ignore[index]


def test_quality_assessment_matches_golden_fixture() -> None:
    text = _golden_input_text()
    assessment = quality_assessment(text)
    expected = _golden_assessment()

    assert assessment.raw_score == pytest.approx(expected["raw_score"], rel=1e-6)
    assert assessment.score == pytest.approx(expected["score"], rel=1e-6)
    assert list(assessment.flags) == pytest.approx(expected["flags"], rel=1e-6)
    assert len(assessment.flags) == len(QUALITY_FLAG_NAMES)
    model_info = quality_model_metadata()
    assert model_info.sha256 is not None



def test_quality_assessment_penalises_high_risk_terms() -> None:
    text = _golden_input_text() + " URGENT update required."
    assessment = quality_assessment(text)
    penalty = quality_module._HIGH_RISK_PENALTY  # type: ignore[attr-defined]

    assert assessment.raw_score > 0
    assert assessment.score == pytest.approx(assessment.raw_score * penalty, rel=1e-6)
    assert assessment.score < assessment.raw_score


def test_explain_score_reports_triggered_flags() -> None:
    text = "The policy includes long sentences with repeated repeated repeated words and complex structures."
    details = explain_score(text)
    triggered = {name for name, value in details["flags"].items() if value >= 0.7}

    assert details["score"] == pytest.approx(quality_assessment(text).score, rel=1e-6)
    for flag in triggered:
        assert f"quality flag triggered: {flag}" in details["rationale"]
    # Ensure at least one rationale references high-risk when terms appear
    risky = explain_score("This URGENT update requires immediate attention.")
    assert any("high-risk" in r for r in risky["rationale"])


def test_quality_scoring_records_model_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    approvals.approvals.clear()
    audit_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    log_calls: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(
        approvals,
        "log_audit_event",
        lambda *args, **kwargs: audit_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        approvals,
        "log_event",
        lambda action, **kwargs: log_calls.append((action, kwargs)),
    )

    text = _golden_input_text()
    approval = approvals.submit_draft_for_approval(
        "wf-quality",
        "alice",
        "doc-qa",
        text,
        critic=None,
        threshold=0.95,
    )

    model_info = approval.scoring_metadata.get("model")  # type: ignore[assignment]
    assert isinstance(model_info, dict)
    assert model_info.get("sha256")
    assert model_info.get("version") is None or isinstance(model_info.get("version"), str)

    audit_models = [kwargs.get("model_sha256") for _, kwargs in audit_calls]
    log_models = [payload.get("model_sha256") for _, payload in log_calls]
    assert model_info["sha256"] in audit_models
    assert model_info["sha256"] in log_models
