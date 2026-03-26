"""Tests for the second batch of release-checklist features.

Covers:
- Reviewer workload dashboard (reporting module + API)
- Document aging metrics (reporting module + API)
- Template phase locking (template_manager module + API)
- Template version change tracking (template_manager module)
- Document pre-flight validation (doc_validation module + API):
  - Acronym validation
  - Heading structure validation
  - Plain language scoring
  - Style validation (AI style pass, toggleable)
  - Composite pre-flight check
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from docreview360 import auth
from docreview360.api import app
from docreview360.approvals import approvals, create_approval
from docreview360.doc_validation import (
    PreflightResult,
    is_ai_style_enabled,
    preflight_validate,
    score_plain_language,
    validate_acronyms,
    validate_heading_structure,
    validate_style,
)
from docreview360.documents import documents, import_document
from docreview360.reporting import document_aging_metrics, reviewer_workload_dashboard
from docreview360.search import ProjectModel, add_project, projects
from docreview360.template_manager import (
    get_template_phase_locks,
    is_template_locked_for_phase,
    list_template_versions,
    lock_template_for_phase,
    reset_template_phase_locks,
    unlock_template_for_phase,
    upload_template,
)
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _clean_template_locks() -> None:  # type: ignore[return]
    reset_template_phase_locks()
    yield
    reset_template_phase_locks()


@pytest.fixture(autouse=True)
def _clean_template_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[return]
    import docreview360.template_manager as tm

    monkeypatch.setattr(tm, "_ACTIVE_TEMPLATES_FILE", tmp_path / "templates_test.json")
    monkeypatch.setattr(tm, "_TEMPLATES_LOADED", False)
    monkeypatch.setattr(tm, "_template_store", {})
    yield
    monkeypatch.setattr(tm, "_template_store", {})


# ---------------------------------------------------------------------------
# Acronym validation
# ---------------------------------------------------------------------------


def test_acronym_no_issues_when_all_defined() -> None:
    text = "The FAA (Federal Aviation Administration) regulates aviation."
    issues = validate_acronyms(text)
    assert not any(i.acronym == "FAA" for i in issues)


def test_acronym_detects_undefined() -> None:
    text = "Please review the SRS document carefully."
    issues = validate_acronyms(text)
    acronyms = {i.acronym for i in issues}
    assert "SRS" in acronyms


def test_acronym_counts_occurrences() -> None:
    text = "The API endpoint. The API should return JSON."
    issues = validate_acronyms(text)
    api_issue = next((i for i in issues if i.acronym == "API"), None)
    assert api_issue is not None
    assert api_issue.occurrences == 2


def test_acronym_definition_via_expansion_first() -> None:
    text = "(Federal Aviation Administration) FAA approved the change."
    issues = validate_acronyms(text)
    assert not any(i.acronym == "FAA" for i in issues)


def test_acronym_empty_text() -> None:
    assert validate_acronyms("") == []


def test_acronym_no_acronyms() -> None:
    text = "This is a simple sentence with no acronyms."
    assert validate_acronyms(text) == []


def test_acronym_multiple_defined() -> None:
    text = "The CIA (Central Intelligence Agency) and FBI (Federal Bureau of Investigation) cooperate."
    issues = validate_acronyms(text)
    acronyms = {i.acronym for i in issues}
    assert "CIA" not in acronyms
    assert "FBI" not in acronyms


# ---------------------------------------------------------------------------
# Heading structure validation
# ---------------------------------------------------------------------------


def test_heading_valid_structure() -> None:
    text = "# Title\n\n## Section\n\n### Sub-section\n"
    issues = validate_heading_structure(text)
    assert issues == []


def test_heading_skipped_level() -> None:
    text = "# Title\n\n### Skipped H2\n"
    issues = validate_heading_structure(text)
    assert any("skipped" in i.issue for i in issues)


def test_heading_multiple_h1() -> None:
    text = "# First Title\n\n# Second Title\n"
    issues = validate_heading_structure(text)
    assert any("multiple H1" in i.issue for i in issues)


def test_heading_empty_text() -> None:
    assert validate_heading_structure("") == []


def test_heading_no_headings() -> None:
    text = "Just some paragraph text without any headings."
    assert validate_heading_structure(text) == []


def test_heading_reports_line_number() -> None:
    text = "# Title\n\n### Skipped\n"
    issues = validate_heading_structure(text)
    assert issues[0].line_number == 3


def test_heading_h2_to_h4_skipped() -> None:
    text = "# Title\n## Section\n#### Deep\n"
    issues = validate_heading_structure(text)
    assert any("H2 -> H4" in i.issue for i in issues)


# ---------------------------------------------------------------------------
# Plain language scoring
# ---------------------------------------------------------------------------


def test_plain_language_empty_text() -> None:
    score = score_plain_language("")
    assert score.total_words == 0
    assert score.grade_level == "N/A"


def test_plain_language_simple_text() -> None:
    text = "The cat sat on the mat. It was a big cat."
    score = score_plain_language(text)
    assert score.flesch_reading_ease > 60


def test_plain_language_score_in_range() -> None:
    score = score_plain_language("Hello world. This is a test sentence.")
    assert 0.0 <= score.flesch_reading_ease <= 100.0


def test_plain_language_total_words() -> None:
    text = "One two three four five."
    score = score_plain_language(text)
    assert score.total_words == 5


def test_plain_language_has_recommendation() -> None:
    score = score_plain_language("The quick brown fox jumps over the lazy dog.")
    assert score.recommendation


def test_plain_language_avg_words_per_sentence_positive() -> None:
    score = score_plain_language("Short sentence. Another one here.")
    assert score.avg_words_per_sentence > 0


# ---------------------------------------------------------------------------
# Style validation
# ---------------------------------------------------------------------------


def test_style_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCREVIEW360_AI_STYLE", raising=False)
    issues = validate_style("We should utilize this approach.")
    assert issues == []


def test_style_enabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_AI_STYLE", "1")
    issues = validate_style("We should utilize this approach.")
    assert any("utilize" in i.matched_text.lower() for i in issues)


def test_style_force_bypasses_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCREVIEW360_AI_STYLE", raising=False)
    issues = validate_style("We should utilize this approach.", force=True)
    assert any("utilize" in i.matched_text.lower() for i in issues)


def test_style_detects_filler_phrase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_AI_STYLE", "1")
    issues = validate_style("Due to the fact that this is important.")
    assert any("due to the fact that" in i.matched_text.lower() for i in issues)


def test_style_reports_line_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_AI_STYLE", "1")
    text = "Line one.\nWe should utilize this.\nLine three."
    issues = validate_style(text)
    utilize_issues = [i for i in issues if "utilize" in i.matched_text.lower()]
    assert utilize_issues[0].line_number == 2


def test_is_ai_style_enabled_false_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DOCREVIEW360_AI_STYLE", raising=False)
    assert is_ai_style_enabled() is False


def test_is_ai_style_enabled_true_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_AI_STYLE", "true")
    assert is_ai_style_enabled() is True


# ---------------------------------------------------------------------------
# Composite pre-flight validation
# ---------------------------------------------------------------------------


def test_preflight_passes_clean_document() -> None:
    text = "# Overview\n\n## Details\n\nThis document describes the system."
    result = preflight_validate(text)
    assert isinstance(result, PreflightResult)
    assert result.passed is True


def test_preflight_fails_on_heading_issues() -> None:
    text = "# Title\n\n### Skipped level\n"
    result = preflight_validate(text, require_valid_headings=True)
    assert result.passed is False
    assert result.heading_issues


def test_preflight_fails_on_undefined_acronyms() -> None:
    text = "The SRS must be reviewed by the CCB."
    result = preflight_validate(text, require_no_undefined_acronyms=True)
    assert result.passed is False
    assert result.acronym_issues


def test_preflight_fails_on_low_reading_ease() -> None:
    # Very complex text with long words
    text = (
        "The multidisciplinary methodology encompasses comprehensive interdisciplinary "
        "collaboration necessitating unprecedented organizational infrastructure reconfiguration. "
        "Notwithstanding aforementioned considerations, telecommunications implementations "
        "demonstrate contradictory performance characteristics."
    )
    result = preflight_validate(text, min_reading_ease=70.0)
    assert result.passed is False


def test_preflight_always_includes_plain_language() -> None:
    result = preflight_validate("Hello world.")
    assert result.plain_language is not None


def test_preflight_to_dict_is_serialisable() -> None:
    import json

    result = preflight_validate("# Title\n\nSimple text.")
    d = result.to_dict()
    # Should not raise
    json.dumps(d)
    assert "passed" in d
    assert "acronym_issues" in d
    assert "heading_issues" in d
    assert "plain_language" in d
    assert "style_issues" in d
    assert "errors" in d


# ---------------------------------------------------------------------------
# Preflight API endpoint
# ---------------------------------------------------------------------------


def test_api_preflight_clean_document() -> None:
    client = TestClient(app)
    resp = client.post(
        "/documents/preflight",
        json={"text": "# Title\n\n## Section\n\nSimple text."},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "passed" in data
    assert "plain_language" in data


def test_api_preflight_heading_failure() -> None:
    client = TestClient(app)
    resp = client.post(
        "/documents/preflight",
        json={"text": "# Title\n\n### Skipped", "require_valid_headings": True},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["passed"] is False


def test_api_preflight_requires_auth() -> None:
    client = TestClient(app)
    resp = client.post("/documents/preflight", json={"text": "hello"})
    assert resp.status_code in {401, 403}


# ---------------------------------------------------------------------------
# Template phase locking (module)
# ---------------------------------------------------------------------------


def test_lock_template_for_phase() -> None:
    lock_template_for_phase("spec-template", "Review")
    assert is_template_locked_for_phase("spec-template", "Review")


def test_unlock_template_for_phase() -> None:
    lock_template_for_phase("spec-template", "Review")
    unlock_template_for_phase("spec-template", "Review")
    assert not is_template_locked_for_phase("spec-template", "Review")


def test_lock_does_not_affect_other_phases() -> None:
    lock_template_for_phase("spec-template", "Review")
    assert not is_template_locked_for_phase("spec-template", "Draft")


def test_unlock_nonexistent_lock_is_noop() -> None:
    unlock_template_for_phase("no-such-template", "Draft")  # Should not raise


def test_get_template_phase_locks_returns_locked_phases() -> None:
    lock_template_for_phase("my-template", "Phase1")
    lock_template_for_phase("my-template", "Phase2")
    locks = get_template_phase_locks("my-template")
    assert "Phase1" in locks
    assert "Phase2" in locks


def test_get_template_phase_locks_empty_for_unlocked() -> None:
    assert get_template_phase_locks("nonexistent-template") == []


def test_lock_prevents_upload() -> None:
    upload_template("locked-tmpl", b"v1 content")
    lock_template_for_phase("locked-tmpl", "Review")
    with pytest.raises(PermissionError):
        upload_template("locked-tmpl", b"v2 content", metadata={"phase": "Review"})


def test_lock_empty_name_raises() -> None:
    with pytest.raises(ValueError):
        lock_template_for_phase("", "Review")


def test_lock_empty_phase_raises() -> None:
    with pytest.raises(ValueError):
        lock_template_for_phase("my-template", "")


# ---------------------------------------------------------------------------
# Template version change tracking (module)
# ---------------------------------------------------------------------------


def test_first_version_has_no_change_summary() -> None:
    ver = upload_template("change-track", b"Initial content")
    assert ver.change_summary == ""


def test_second_version_has_change_summary() -> None:
    upload_template("change-track", b"Initial content\nLine two\n")
    ver2 = upload_template("change-track", b"Initial content\nLine two modified\n")
    assert ver2.change_summary != ""
    assert ver2.change_summary != "no changes detected"


def test_identical_content_reports_no_changes() -> None:
    content = b"Same content line\n"
    upload_template("same-content", content)
    ver2 = upload_template("same-content", content)
    assert ver2.change_summary == "no changes detected"


def test_change_summary_shows_diff_markers() -> None:
    upload_template("diff-test", b"Hello world\n")
    ver2 = upload_template("diff-test", b"Hello universe\n")
    # Unified diff will contain --- or +++
    assert "---" in ver2.change_summary or "@@" in ver2.change_summary


def test_version_history_includes_all_versions() -> None:
    upload_template("history-tmpl", b"v1")
    upload_template("history-tmpl", b"v2")
    upload_template("history-tmpl", b"v3")
    versions = list_template_versions("history-tmpl")
    assert len(versions) == 3
    assert versions[0].version == 1
    assert versions[2].version == 3


# ---------------------------------------------------------------------------
# Template locking API endpoints
# ---------------------------------------------------------------------------


def test_api_lock_template_phase() -> None:
    upload_template("api-lock-tmpl", b"content")
    client = TestClient(app)
    resp = client.put("/templates/api-lock-tmpl/locks/Review", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["locked"] is True
    assert data["phase"] == "Review"


def test_api_unlock_template_phase() -> None:
    lock_template_for_phase("api-unlock-tmpl", "Draft")
    client = TestClient(app)
    resp = client.delete("/templates/api-unlock-tmpl/locks/Draft", headers=_alice_headers())
    assert resp.status_code == 204
    assert not is_template_locked_for_phase("api-unlock-tmpl", "Draft")


def test_api_list_template_locks() -> None:
    lock_template_for_phase("api-list-tmpl", "Review")
    lock_template_for_phase("api-list-tmpl", "Final")
    client = TestClient(app)
    resp = client.get("/templates/api-list-tmpl/locks", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "Review" in data["locked_phases"]
    assert "Final" in data["locked_phases"]


def test_api_list_template_versions() -> None:
    upload_template("api-versions-tmpl", b"version one")
    upload_template("api-versions-tmpl", b"version two")
    client = TestClient(app)
    resp = client.get("/templates/api-versions-tmpl/versions", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["version"] == 1
    assert data[1]["version"] == 2
    assert "change_summary" in data[1]


def test_api_list_template_versions_not_found() -> None:
    client = TestClient(app)
    resp = client.get("/templates/no-such-template-xyz/versions", headers=_alice_headers())
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Reviewer workload dashboard (module)
# ---------------------------------------------------------------------------


def test_reviewer_workload_empty() -> None:
    approvals.clear()
    result = reviewer_workload_dashboard()
    # May have entries from other tests; at minimum must be a list
    assert isinstance(result, list)


def test_reviewer_workload_counts_pending() -> None:
    approvals.clear()
    projects.clear()
    doc = import_document("WL doc", b"content")
    add_project(ProjectModel(id="wl-proj", name="Workload Project"))
    create_approval("wf-wl-carol", "carol", doc.id)
    create_approval("wf-wl-carol2", "carol", doc.id)
    result = reviewer_workload_dashboard()
    carol_entry = next((r for r in result if r.reviewer == "carol"), None)
    assert carol_entry is not None
    assert carol_entry.pending_approvals == 2


def test_reviewer_workload_sorted_by_pending_desc() -> None:
    approvals.clear()
    projects.clear()
    doc = import_document("Sort doc", b"content")
    # dave gets 1 pending, eve gets 3 pending
    create_approval("wf-sort-dave", "dave", doc.id)
    for i in range(3):
        create_approval(f"wf-sort-eve-{i}", "eve", doc.id)
    result = reviewer_workload_dashboard()
    pending_vals = [r.pending_approvals for r in result if r.reviewer in {"dave", "eve"}]
    assert pending_vals == sorted(pending_vals, reverse=True)


def test_reviewer_workload_assigned_projects() -> None:
    approvals.clear()
    projects.clear()
    add_project(ProjectModel(id="p1", name="P1", user="frank"))
    add_project(ProjectModel(id="p2", name="P2", user="frank"))
    doc = import_document("proj doc", b"content")
    create_approval("wf-frank", "frank", doc.id)
    result = reviewer_workload_dashboard()
    frank_entry = next((r for r in result if r.reviewer == "frank"), None)
    assert frank_entry is not None
    assert frank_entry.assigned_projects == 2


# ---------------------------------------------------------------------------
# Reviewer workload dashboard API
# ---------------------------------------------------------------------------


def test_api_reviewer_workload_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/dashboard/reviewer-workload", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_api_reviewer_workload_requires_auth() -> None:
    client = TestClient(app)
    resp = client.get("/dashboard/reviewer-workload")
    assert resp.status_code in {401, 403}


# ---------------------------------------------------------------------------
# Document aging metrics (module)
# ---------------------------------------------------------------------------


def test_document_aging_returns_report() -> None:
    report = document_aging_metrics()
    assert report.total_documents >= 0
    assert isinstance(report.entries, list)


def test_document_aging_counts_known_age() -> None:
    documents.clear()
    old_doc = import_document("Old doc", b"content")
    # Manually set the creation date to 45 days ago
    old_doc.date = datetime.now(timezone.utc) - timedelta(days=45)
    documents[old_doc.id] = old_doc

    report = document_aging_metrics()
    assert report.documents_with_known_age >= 1
    assert report.documents_older_than_30_days >= 1
    assert report.oldest_age_days is not None
    assert report.oldest_age_days >= 44


def test_document_aging_no_docs() -> None:
    documents.clear()
    report = document_aging_metrics()
    assert report.total_documents == 0
    assert report.avg_age_days is None


def test_document_aging_avg_age() -> None:
    documents.clear()
    d1 = import_document("D1", b"x")
    d1.date = datetime.now(timezone.utc) - timedelta(days=10)
    documents[d1.id] = d1

    d2 = import_document("D2", b"y")
    d2.date = datetime.now(timezone.utc) - timedelta(days=20)
    documents[d2.id] = d2

    report = document_aging_metrics()
    assert report.avg_age_days is not None
    # Average should be ~15 days
    assert 13 <= report.avg_age_days <= 17


def test_document_aging_older_than_90() -> None:
    documents.clear()
    d = import_document("Very old", b"x")
    d.date = datetime.now(timezone.utc) - timedelta(days=100)
    documents[d.id] = d

    report = document_aging_metrics()
    assert report.documents_older_than_90_days >= 1


# ---------------------------------------------------------------------------
# Document aging API
# ---------------------------------------------------------------------------


def test_api_document_aging_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/reports/document-aging", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "total_documents" in data
    assert "entries" in data
    assert "generated_at" in data


def test_api_document_aging_requires_auth() -> None:
    client = TestClient(app)
    resp = client.get("/reports/document-aging")
    assert resp.status_code in {401, 403}
