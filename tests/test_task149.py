from docuflow.schedule_editor import load_schedules
from docuflow.stubs.task149 import task149


def test_task149_completed(tmp_path) -> None:
    path = tmp_path / "sched.yaml"
    task149(path=path)
    assert load_schedules(path)["escalation"] == "0 3 * * *"
