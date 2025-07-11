from docreview360.stubs.task77 import CamundaClient


def test_start_process() -> None:
    client = CamundaClient()
    proc_id = client.start_process("wf123")
    assert proc_id == "started:wf123"
