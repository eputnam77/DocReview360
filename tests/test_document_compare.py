import pytest

from docreview360.document_compare import influence_map, track_changes, version_similarity


def test_document_compare_utils():
    a = "hello\nworld"
    b = "hello\nthere world"
    sim = version_similarity(a, b)
    assert 0 <= sim <= 1
    diff = track_changes(a, b)
    assert diff
    mapping = influence_map({"a": a, "b": b}, threshold=0.0)
    assert ("a", "b") in mapping


def test_influence_map_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        influence_map({"a": "x", "b": "y"}, threshold=1.5)
