from docuflow.rbac_editor import load_rbac
from docuflow.stubs.task148 import task148


def test_task148_completed(tmp_path) -> None:
    path = tmp_path / "rbac.yaml"
    task148(path=path)
    assert load_rbac(path)["pm"]["delete_project"] is False
