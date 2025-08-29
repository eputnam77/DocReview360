from __future__ import annotations

from typing import Any

import docreview360.event_dispatcher as ed_module
from docreview360.event_dispatcher import EventDispatcher, dead_letter_queue


def test_event_dispatcher_avoids_final_sleep(monkeypatch):
    """Ensure the dispatcher does not sleep after the final retry."""

    calls: list[float] = []

    def fake_post(*a: Any, **k: Any):  # always fails
        class Resp:
            status_code = 500

        return Resp()

    def fake_sleep(duration: float) -> None:
        calls.append(duration)

    monkeypatch.setattr(ed_module, "http_post", fake_post)
    monkeypatch.setattr(ed_module.time, "sleep", fake_sleep)
    dead_letter_queue.clear()

    dispatcher = EventDispatcher(retries=3, backoff=1)
    dispatcher.send("url", "evt", {})

    # With exponential backoff starting at 1 the sleeps should be 1 and 2
    assert calls == [1, 2]
    assert dead_letter_queue  # ensure failure recorded
