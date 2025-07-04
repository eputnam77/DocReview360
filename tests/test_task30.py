from docuflow.stubs.task30 import task30


def test_task30_celery_echo() -> None:
    assert task30("hello") == "hello"
