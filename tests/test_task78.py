from docuflow.stubs.task78 import ImixsAdapter


def test_start_workflow() -> None:
    adapter = ImixsAdapter()
    assert adapter.start_workflow("flow1") == "imixs:flow1"
