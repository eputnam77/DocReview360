"""Tests covering sanitisation of comment text."""

from docreview360 import comments


def test_add_comment_escapes_html_and_preserves_mentions() -> None:
    comment = comments.add_comment("doc", "user", "<script>alert('x')</script> hello @alice")

    assert comment.text == "&lt;script&gt;alert('x')&lt;/script&gt; hello @alice"
    assert comment.raw_text == "<script>alert('x')</script> hello @alice"
    assert comment.mentions == ["alice"]


def test_render_comment_for_response_returns_sanitised_copy() -> None:
    original = comments.add_comment("doc", "user", "& already safe @bob")

    rendered = comments.render_comment_for_response(original)

    assert rendered is not original
    assert rendered.text == "&amp; already safe @bob"
    assert rendered.raw_text == "& already safe @bob"
    assert rendered.mentions == ["bob"]
