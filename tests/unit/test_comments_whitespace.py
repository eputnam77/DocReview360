import pytest

from docreview360 import comments


def test_add_comment_rejects_whitespace_only_text() -> None:
    """Whitespace-only comments should raise ``ValueError``."""
    with pytest.raises(ValueError):
        comments.add_comment("doc", "user", "   ")
