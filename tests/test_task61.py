from docuflow.pandiff import format_change_bars


def test_track_changes_output() -> None:
    lines = format_change_bars("a\nb", "a\nc")
    assert "[-] b" in lines
    assert "[+] c" in lines
