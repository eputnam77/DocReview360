from docreview360.stubs.task85 import apply_preferences


def test_apply_preferences() -> None:
    prefs = apply_preferences(True, False)
    assert prefs == {"dark_mode": True, "reduce_motion": False}
