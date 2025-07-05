import string
from pathlib import Path

from cryptography.fernet import Fernet
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from docuflow.stubs.task90 import create_backup


@given(value=st.text(alphabet=string.ascii_letters, min_size=1))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_task90_property(value: str, tmp_path: Path) -> None:
    dest = tmp_path / f"{value}.bak"
    key = create_backup(dest, value)
    assert Fernet(key).decrypt(dest.read_bytes()) == value.encode()
