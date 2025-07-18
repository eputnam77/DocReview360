from docreview360.stubs.task220 import piv_cac_login


def test_task220_piv_cac_login() -> None:
    """PIV/CAC certificate authentication should succeed."""
    piv_cac_login(b"cert")
