"""Event dispatcher with retry/backoff and dead-letter queue."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Dict, List

from .http_client import post as http_post

if TYPE_CHECKING:
    from .workflows import WorkflowModel

# in-memory store of failed events for inspection or replay
# Each item is a dict with ``url``, ``event`` and ``payload`` keys
dead_letter_queue: List[dict[str, object]] = []


class EventDispatcher:
    """Send events to callbacks with retry and backoff."""

    def __init__(self, retries: int = 3, backoff: float = 0.1) -> None:
        if retries < 1:
            raise ValueError("retries must be at least 1")
        # ``time.sleep`` raises ``ValueError`` when passed a negative value. If
        # callers accidentally supply a negative backoff, the exception would be
        # raised deep inside :meth:`send` after the first failed request rather
        # than at construction time.  Validate the argument eagerly so misuse is
        # reported with a clear error message.
        if backoff < 0:
            raise ValueError("backoff must be non-negative")
        self.retries = retries
        self.backoff = backoff

    def send(self, url: str, event: str, payload: Dict[str, object]) -> None:
        """POST ``payload`` to ``url``; retry on failure and record dead letters."""
        delay = self.backoff
        for attempt in range(self.retries):
            try:
                response = http_post(
                    url,
                    json={"event": event, "payload": payload},
                    timeout=5,
                )
                if response.status_code < 400:
                    return
            except Exception:  # pragma: no cover - network errors
                pass
            # ``time.sleep`` was previously called unconditionally which meant
            # we slept once more even after the final failed attempt.  This
            # unnecessarily slowed down callers without offering any benefit.
            # Only sleep when another retry will be attempted.
            if attempt < self.retries - 1:
                time.sleep(delay)
                delay *= 2
        # ``payload`` may be mutated by callers after ``send`` returns. Store a
        # deep copy so the dead letter queue preserves the original event data
        # for later inspection or replay.
        from copy import deepcopy

        dead_letter_queue.append(
            {"url": url, "event": event, "payload": deepcopy(payload)}
        )


_dispatcher = EventDispatcher()


def dispatch_workflow_event(workflow: "WorkflowModel") -> None:
    """Dispatch workflow status or completion events to its callback URL."""
    url = getattr(workflow, "callback_url", None)
    if not url:
        return
    if getattr(workflow, "phase", None) and getattr(workflow, "phases", []):
        event = "workflow.completed" if workflow.phase == workflow.phases[-1] else "workflow.status"
    else:
        event = "workflow.status"
    _dispatcher.send(url, event, workflow.model_dump())
