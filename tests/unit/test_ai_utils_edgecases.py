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
