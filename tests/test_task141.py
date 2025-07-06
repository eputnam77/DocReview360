from docuflow.stubs.task141 import task141


def test_task141_completed(tmp_path) -> None:
    cfg = tmp_path / "cfg.yaml"
    task141(path=cfg)
    assert cfg.exists()
