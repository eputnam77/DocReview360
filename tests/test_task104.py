from docreview360.fed_numbering import can_toggle_numbering


def test_can_toggle_numbering() -> None:
    rbac = {"admin": {"toggle_numbering": True}, "viewer": {"toggle_numbering": False}}
    assert can_toggle_numbering("admin", rbac)
    assert not can_toggle_numbering("viewer", rbac)
    assert not can_toggle_numbering("missing", rbac)


def test_can_toggle_numbering_handles_none() -> None:
    """Gracefully handle roles with ``None`` permission mapping."""
    rbac = {"admin": None}
    assert not can_toggle_numbering("admin", rbac)
