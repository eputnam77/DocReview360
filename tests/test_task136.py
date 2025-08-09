import pytest

from docreview360.stubs.task136 import task136


class Dummy:
    pass


@pytest.mark.asyncio
async def test_task136_completed(monkeypatch):
    calls: list[int] = []

    async def fake_launch(app, port: int = 5555, work_dir: str = ".") -> None:
        calls.append(port)

    monkeypatch.setattr("docreview360.stubs.task136.launch_flower", fake_launch)
    await task136(Dummy())
    assert calls == [5555]
