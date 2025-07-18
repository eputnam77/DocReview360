from docreview360.stubs.task85 import apply_preferences


def test_apply_preferences() -> None:
    prefs = apply_preferences("dark", False)
    assert prefs == {"theme": "dark", "reduce_motion": False}
