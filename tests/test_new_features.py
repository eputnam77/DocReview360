import json
from datetime import datetime, timedelta

import pytest

from docreview360 import ai_utils, quality, search
from docreview360.fann_model import Weights


def test_fann_score_respects_explicit_weights(monkeypatch):
    """Providing an explicit empty weight vector should not fall back to defaults."""
    # Avoid running the external GovDocVerify dependency during tests
    monkeypatch.setattr(ai_utils, "_gov_run", None)

    zero_weights = [0.0] * len(ai_utils.FANN_FEATURE_NAMES)
    score = ai_utils._fann_score("Example text", zero_weights)
    assert score == pytest.approx(0.5, abs=1e-6)


def test_initialize_high_risk_terms_case_insensitive(tmp_path):
    """Loaded high risk terms should match regardless of case."""

    data_path = tmp_path / "terms.json"
    data_path.write_text(json.dumps(["Risky"]))

    quality.initialize_high_risk_terms(data_path)
    try:
        assert quality.high_risk_warnings("This is RISKY") == ["risky"]
    finally:
        # Restore default configuration so other tests remain unaffected
        quality.initialize_high_risk_terms()


def test_assign_temporary_accepts_naive_datetime():
    """Naive datetimes should be interpreted as UTC rather than raising."""

    proj = search.ProjectModel(id="tmp-proj", name="Temp")
    search.add_project(proj)
    try:
        until = datetime.utcnow() + timedelta(days=1)
        search.assign_temporary(proj.id, "bob", until)
        stored = search.projects[proj.id]
        assert stored.temp_user == "bob"
        assert stored.temp_until.tzinfo is not None
    finally:
        search.projects.pop(proj.id, None)


def test_template_and_prompt_helpers(monkeypatch):
    """Exercise feedback/prompt template registration and rendering."""
    monkeypatch.setattr(ai_utils, "_gov_run", None)

    ai_utils.add_feedback_template("greet", "Hello {text}!")
    assert ai_utils.generate_feedback("greet", "Bob") == "Hello Bob!"

    ai_utils.add_prompt_template("echo", "Say {word}")
    assert ai_utils.render_prompt("echo", word="hi") == "Say hi"


def test_synth_compress_and_validation(monkeypatch):
    monkeypatch.setattr(ai_utils, "synth_enabled", True)
    # stop words and vowels removed
    assert ai_utils.synth_compress("This is an example") == "Ths xmpl"

    # validate_content with diagnostics
    ok, diag = ai_utils.validate_content("Valid text", return_diagnostics=True)
    assert ok is True and diag["is_valid"] is True


def test_quality_scoring(monkeypatch, tmp_path):
    monkeypatch.setattr(ai_utils, "_gov_run", None)

    weights = Weights(w1=[[0.0]*6 for _ in range(4)], b1=[0.0]*4, w2=[0.0]*4, b2=0.0)
    text = "This report avoids URGENT terms."  # contains risky word
    score = quality.approval_likelihood(text, weights, doc_type="policy_memo")
    assert 0 < score < 0.5  # penalised due to high-risk term

    expl = quality.explain_score(text, weights, doc_type="policy_memo")
    assert any("high-risk" in r for r in expl["rationale"])


def test_template_error_paths(monkeypatch):
    monkeypatch.setattr(ai_utils, "_gov_run", None)

    with pytest.raises(ValueError):
        ai_utils.apply_feedback_template("No placeholder", "x")

    with pytest.raises(ValueError):
        ai_utils.add_feedback_template("bad", "oops")

    with pytest.raises(ValueError):
        ai_utils.add_prompt_template("bad", "no vars here")

    ai_utils.add_prompt_template("need", "{word}")
    with pytest.raises(ValueError):
        ai_utils.render_prompt("need")  # missing placeholder


def test_structure_and_export(monkeypatch):
    monkeypatch.setattr(ai_utils, "_gov_run", lambda *a, **k: {"styleIssues": [1]})

    # style_guide_score via govdocverify branch
    assert ai_utils.style_guide_score("Good sentence.") < 1

    assert ai_utils.structural_pattern_score("") == 0.0
    text = "# H1\n## H2\n- item\n1. num"
    assert ai_utils.structural_pattern_score(text) > 0

    assert ai_utils.suggest_export_format("contains image") == "pdf"
    assert ai_utils.suggest_export_format("contains table") == "xlsx"
    assert ai_utils.suggest_export_format("plain text") == "markdown"


def test_create_validated_document(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_utils, "_gov_run", None)

    path = tmp_path / "file.txt"
    data = b"content"
    doc = ai_utils.create_validated_document(path.name, data)
    assert doc.content == "content"

    with pytest.raises(ValueError):
        ai_utils.create_validated_document("bad.txt", b"")
