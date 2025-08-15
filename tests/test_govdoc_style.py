import docreview360.ai_utils as ai_utils


def test_style_guide_score_uses_govdocverify(monkeypatch):
    def fake_run(path: str, doc_type: str):
        return {"styleIssues": ["issue"]}

    monkeypatch.setattr(ai_utils, "_gov_run", fake_run)
    # Heuristic score would be 1.0, but GovDocVerify reports an issue
    assert ai_utils.style_guide_score("Good sentence.") == 0.0
