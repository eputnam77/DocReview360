import pytest

from docreview360.stubs.task137 import task137


@pytest.mark.asyncio
async def test_task137_completed(monkeypatch):
    def fake_run(args, check):
        assert "helm_smoke.py" in args[-1]

    monkeypatch.setattr("subprocess.run", fake_run)
    await task137()
