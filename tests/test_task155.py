from docuflow.stubs.task155 import task155


def test_task155_completed() -> None:
    plan = """
      + aws_instance.example
      ~ aws_db_instance.example
    """
    actions = task155(plan)
    assert {"action": "create", "resource": "aws_instance.example"} in actions
    assert {"action": "update", "resource": "aws_db_instance.example"} in actions


def test_task155_empty() -> None:
    assert task155("") == []
