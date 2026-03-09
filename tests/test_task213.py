from docreview360.approvals import run_confirmed_action


def test_task213_confirm_runs_action() -> None:
    called = False

    def do() -> None:
        nonlocal called
        called = True

    assert run_confirmed_action(True, do)
    assert called


def test_task213_cancel() -> None:
    called = False

    def do() -> None:
        nonlocal called
        called = True

    assert not run_confirmed_action(False, do)
    assert not called
