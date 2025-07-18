from docreview360.stubs.task222 import set_user_theme


def test_task222_set_user_theme() -> None:
    """Users can save a light or dark theme preference."""
    set_user_theme("u1", "dark")
