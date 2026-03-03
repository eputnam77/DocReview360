import importlib.util
from datetime import datetime, timezone
from pathlib import Path


def _load_run_e2e_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_e2e.py"
    spec = importlib.util.spec_from_file_location("docreview360_run_e2e", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_now_run_id_uses_utc_timezone(monkeypatch) -> None:
    run_e2e = _load_run_e2e_module()

    class _FixedDateTime:
        @staticmethod
        def now(tz=None):
            assert tz is timezone.utc
            return datetime(2026, 3, 1, 12, 34, 56, tzinfo=timezone.utc)

    monkeypatch.setattr(run_e2e, "datetime", _FixedDateTime)

    assert run_e2e._now_run_id() == "20260301-123456"


def test_resolve_run_root_uses_explicit_run_id(monkeypatch) -> None:
    run_e2e = _load_run_e2e_module()
    monkeypatch.setenv("E2E_RUN_ID", "fixed-run")
    monkeypatch.delenv("E2E_RUN_DIR", raising=False)

    run_id, run_root = run_e2e._resolve_run_root()

    assert run_id == "fixed-run"
    assert run_root == Path(".e2e-runs") / "fixed-run"


def test_resolve_run_root_prefers_explicit_directory(monkeypatch, tmp_path: Path) -> None:
    run_e2e = _load_run_e2e_module()
    monkeypatch.setenv("E2E_RUN_ID", "ignored-run-id")
    monkeypatch.setenv("E2E_RUN_DIR", str(tmp_path / "deterministic-e2e"))

    run_id, run_root = run_e2e._resolve_run_root()

    assert run_id == "ignored-run-id"
    assert run_root == tmp_path / "deterministic-e2e"
