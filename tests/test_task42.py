from docuflow.markreview import apply_markreview


def test_apply_markreview() -> None:
    diff = apply_markreview("line1", "line1\nnew")
    assert "[+] new" in diff
