import pytest

from docreview360 import ai_utils


def test_synth_compress_handles_empty_stopwords(monkeypatch):
    monkeypatch.setattr(ai_utils, "synth_enabled", True)
    monkeypatch.setattr(ai_utils, "SYNTH_STOP_WORDS", set())
    # Should not raise when no stop words are configured
    assert ai_utils.synth_compress("This is a test")


def test_create_validated_document_invalid_utf8():
    with pytest.raises(ValueError):
        ai_utils.create_validated_document("f.txt", b"\xff\xfe\x00\x00")


def test_fann_features_unique_ratio_token_based():
    """Unique ratio should consider tokens rather than raw characters."""
    feats = ai_utils._fann_features("aa aa")
    # Two words with one unique token => ratio 0.5
    assert feats[1] == pytest.approx(0.5)
