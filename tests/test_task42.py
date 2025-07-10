from docuflow.pandiff import format_change_bars


def test_format_change_bars() -> None:
    lines = format_change_bars("line1", "line1\nnew")
    assert "[+] new" in lines
