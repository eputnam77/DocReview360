import pytest

from docuflow.stubs.task136 import task136


class Dummy:
    pass


@pytest.mark.asyncio
async def test_task136_completed(monkeypatch):
    async def fake_launch(app, port=5555, work_dir="."):
        assert port == 5555

    monkeypatch.setattr("docuflow.stubs.task136.launch_flower", fake_launch)
    await task136(Dummy())
