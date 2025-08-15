from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from docreview360.ai_balancer import (
    assign_job,
    load_state,
    register_worker,
    reset,
    save_state,
    _workers,
)


def test_save_and_load_workers(tmp_path: Path) -> None:
    reset()
    register_worker("alice")
    assign_job()
    state = tmp_path / "workers.json"
    save_state(state)
    reset()
    assert _workers == {}
    load_state(state)
    assert _workers == {"alice": 1}


def test_api_hooks_load_and_save(tmp_path: Path, monkeypatch) -> None:
    state_file = tmp_path / "state.json"
    monkeypatch.setenv("DOCREVIEW360_WORKER_STATE", str(state_file))

    import docreview360.api as api
    importlib.reload(api)

    called: list[tuple[str, Path]] = []
    monkeypatch.setattr(api, "load_worker_state", lambda p: called.append(("load", p)))
    monkeypatch.setattr(api, "save_worker_state", lambda p: called.append(("save", p)))

    with TestClient(api.app) as client:
        client.get("/health")

    assert ("load", api.WORKER_STATE_FILE) in called
    assert ("save", api.WORKER_STATE_FILE) in called
