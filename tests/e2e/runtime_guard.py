from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

_UNHANDLED_REJECTION_INIT_SCRIPT = """
() => {
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event.reason;
    let detail = "Unknown unhandled rejection";
    if (reason instanceof Error) {
      detail = reason.stack || reason.message || String(reason);
    } else if (typeof reason === "string") {
      detail = reason;
    } else {
      try {
        detail = JSON.stringify(reason);
      } catch (_) {
        detail = String(reason);
      }
    }
    console.error(`[e2e-unhandledrejection] ${detail}`);
  });
}
"""

_IGNORED_REQUEST_FAILURES = (
    "net::ERR_ABORTED",
    "NS_BINDING_ABORTED",
)


@dataclass(frozen=True)
class RuntimeIssue:
    kind: str
    url: str
    detail: str


def _read_text_attr(value: Any, attr: str) -> str:
    current = getattr(value, attr, "")
    return str(current() if callable(current) else current)


def _request_failure_text(request: Any) -> str:
    failure = getattr(request, "failure", None)
    if callable(failure):
        failure = failure()
    if isinstance(failure, dict):
        return str(failure.get("errorText", ""))
    if failure is None:
        return ""
    if isinstance(failure, str):
        return failure
    error_text = getattr(failure, "error_text", None)
    if callable(error_text):
        error_text = error_text()
    if error_text is not None:
        return str(error_text)
    return str(failure)


class FrontendCrashGate:
    def __init__(self) -> None:
        self._issues: list[RuntimeIssue] = []
        self._page: Any | None = None

    def attach(self, page: Any) -> None:
        self._page = page
        page.add_init_script(_UNHANDLED_REJECTION_INIT_SCRIPT)
        page.on("pageerror", self._on_page_error)
        page.on("console", self._on_console)
        page.on("requestfailed", self._on_request_failed)

    def assert_clean(self, *, test_id: str) -> None:
        if not self._issues:
            return
        first = self._issues[0]
        lines = [
            f"Frontend runtime crash gate failed in {test_id}.",
            f"First issue: {first.kind} at {first.url}",
            f"Detail: {first.detail}",
        ]
        if len(self._issues) > 1:
            lines.append("Additional issues:")
            for issue in self._issues[1:]:
                lines.append(f"- {issue.kind} at {issue.url}: {issue.detail}")
        pytest.fail("\n".join(lines), pytrace=False)

    def _record(self, *, kind: str, detail: str, url: str | None = None) -> None:
        location = url or self._current_url()
        normalized = " ".join(detail.split()) if detail.strip() else "No detail provided"
        self._issues.append(RuntimeIssue(kind=kind, url=location, detail=normalized))

    def _current_url(self) -> str:
        if self._page is None:
            return "<unknown>"
        current = getattr(self._page, "url", "")
        return str(current() if callable(current) else current or "<unknown>")

    def _on_page_error(self, error: Any) -> None:
        detail = _read_text_attr(error, "message") or str(error)
        self._record(kind="pageerror", detail=detail)

    def _on_console(self, message: Any) -> None:
        message_type = _read_text_attr(message, "type")
        if message_type != "error":
            return
        detail = _read_text_attr(message, "text") or str(message)
        kind = "unhandledrejection" if "[e2e-unhandledrejection]" in detail else "console.error"
        self._record(kind=kind, detail=detail)

    def _on_request_failed(self, request: Any) -> None:
        failure_text = _request_failure_text(request)
        if any(ignored in failure_text for ignored in _IGNORED_REQUEST_FAILURES):
            return
        url = _read_text_attr(request, "url") or self._current_url()
        method = _read_text_attr(request, "method") or "UNKNOWN"
        detail = f"{method} {url}"
        if failure_text:
            detail = f"{detail} failed: {failure_text}"
        self._record(kind="requestfailed", detail=detail, url=url)
