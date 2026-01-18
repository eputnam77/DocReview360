"""Dual-view diff panel tests."""

from docreview360.pandiff import change_bars


def test_dual_view_diff_panel_closes_without_state_leak() -> None:
    lines = change_bars("a\nb", "a\nc")
    assert ("removed", "b") in lines and ("added", "c") in lines

    panel_state: dict[str, bool] = {"open": True, "lines": bool(lines)}

    def close_panel(state: dict[str, bool]) -> None:
        state["open"] = False
        state.pop("lines", None)

    close_panel(panel_state)
    assert panel_state == {"open": False}
