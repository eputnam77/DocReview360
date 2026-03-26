import json
import subprocess
from pathlib import Path

import pytest
from docreview360 import performance_baseline as perf


def test_measure_concurrency_transition_seconds_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        perf.measure_concurrency_transition_seconds(0)


def test_collect_performance_baseline_uses_expected_medians(monkeypatch: pytest.MonkeyPatch) -> None:
    document_samples = iter([0.04, 0.02, 0.03])
    transition_samples = iter([0.005, 0.004, 0.003, 0.004, 0.005])

    monkeypatch.setattr(perf, "measure_api_cold_start_seconds", lambda: 1.25)
    monkeypatch.setattr(perf, "measure_document_load_50_page_seconds", lambda: next(document_samples))
    monkeypatch.setattr(perf, "measure_approval_transition_seconds", lambda: next(transition_samples))

    def _measure_concurrency(concurrency: int) -> float:
        return {10: 0.05, 25: 0.125}[concurrency]

    monkeypatch.setattr(perf, "measure_concurrency_transition_seconds", _measure_concurrency)

    payload = perf.collect_performance_baseline()

    assert payload["api_cold_start_seconds"] == 1.25
    assert payload["document_load_50_page_seconds"] == 0.03
    assert payload["approval_transition_seconds"] == 0.004
    assert payload["concurrency"]["simultaneous_reviewers_10"]["avg_transition_ms"] == 5.0
    assert payload["concurrency"]["simultaneous_reviewers_25"]["avg_transition_ms"] == 5.0


def test_write_performance_baseline_outputs_json_and_markdown(tmp_path: Path) -> None:
    payload = {
        "measured_at": "2026-03-01T00:00:00Z",
        "api_cold_start_seconds": 1.0,
        "document_load_50_page_seconds": 0.02,
        "approval_transition_seconds": 0.004,
        "concurrency": {
            "simultaneous_reviewers_10": {"total_seconds": 0.04, "avg_transition_ms": 4.0},
            "simultaneous_reviewers_25": {"total_seconds": 0.12, "avg_transition_ms": 4.8},
        },
    }

    json_path = perf.write_performance_baseline_json(tmp_path / "perf" / "baseline.json", payload)
    markdown_path = perf.write_performance_baseline_markdown(tmp_path / "docs" / "perf.md", payload)

    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded == payload

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "# Performance Baseline (v0.1)" in markdown
    assert "`1.0s`" in markdown
    assert "`0.02s`" in markdown
    assert "`0.004s`" in markdown


def test_measure_api_cold_start_injects_src_pythonpath(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(
        cmd: list[str],
        *,
        check: bool,
        env: dict[str, str],
        capture_output: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[bytes]:
        captured["cmd"] = cmd
        captured["check"] = check
        captured["env"] = env
        captured["capture_output"] = capture_output
        captured["timeout"] = timeout
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    clock = iter([10.0, 11.75])

    monkeypatch.setattr(perf.subprocess, "run", _fake_run)
    monkeypatch.setattr(perf, "perf_counter", lambda: next(clock))

    measured = perf.measure_api_cold_start_seconds()

    assert measured == 1.75
    assert captured["timeout"] == 30
    env = captured["env"]
    assert isinstance(env, dict)
    pythonpath = env.get("PYTHONPATH", "")
    src_dir = str(Path(perf.__file__).resolve().parents[1])
    assert pythonpath.split(perf.os.pathsep)[0] == src_dir
