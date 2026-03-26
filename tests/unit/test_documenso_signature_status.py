import pytest
from docreview360 import documenso


class _DocumensoOnlyProvider:
    name = "documenso"


def test_signature_status_handles_missing_documenso_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(documenso, "get_provider", lambda: _DocumensoOnlyProvider())

    def _raise_missing(sig_id: str) -> str:
        raise KeyError(f"Unknown signature id {sig_id}")

    monkeypatch.setattr(documenso, "_doc_signature_status", _raise_missing)

    with pytest.raises(KeyError):
        documenso.signature_status("missing")
