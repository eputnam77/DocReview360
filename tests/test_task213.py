from docreview360.stubs.task213 import task213


def test_task213_confirm_runs_action() -> None:
    called = False

    def do() -> None:
        nonlocal called
        called = True

    assert task213(True, do)
    assert called


def test_task213_cancel() -> None:
    called = False

    def do() -> None:
        nonlocal called
        called = True

    assert not task213(False, do)
    assert not called
