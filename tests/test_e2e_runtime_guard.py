from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys

import pytest


def _load_runtime_guard_module():
    module_path = Path(__file__).resolve().parent / "e2e" / "runtime_guard.py"
    module_name = "docreview360_e2e_runtime_guard"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


runtime_guard = _load_runtime_guard_module()
_UNHANDLED_REJECTION_INIT_SCRIPT = runtime_guard._UNHANDLED_REJECTION_INIT_SCRIPT
FrontendCrashGate = runtime_guard.FrontendCrashGate
RuntimeIssue = runtime_guard.RuntimeIssue
_request_failure_text = runtime_guard._request_failure_text


class FakePage:
    def __init__(self, url: str = "http://frontend.local/projects") -> None:
        self.url = url
        self.init_scripts: list[str] = []
        self.handlers: dict[str, object] = {}

    def add_init_script(self, script: str) -> None:
        self.init_scripts.append(script)

    def on(self, event: str, handler: object) -> None:
        self.handlers[event] = handler


@dataclass
class FakeConsoleMessage:
    type: str
    text: str


@dataclass
class FakeRequest:
    url: str
    method: str = "GET"
    failure: object | None = None


def test_attach_registers_expected_handlers_and_script() -> None:
    gate = FrontendCrashGate()
    page = FakePage()

    gate.attach(page)

    assert page.init_scripts == [_UNHANDLED_REJECTION_INIT_SCRIPT]
    assert set(page.handlers) == {"pageerror", "console", "requestfailed"}


def test_console_error_is_recorded_and_warnings_are_ignored() -> None:
    gate = FrontendCrashGate()
    page = FakePage()
    gate.attach(page)

    console_handler = page.handlers["console"]
    console_handler(FakeConsoleMessage(type="warning", text="ignore me"))
    console_handler(FakeConsoleMessage(type="error", text="boom"))

    issues = gate._issues  # noqa: SLF001 - verify test-only runtime gate behavior
    assert issues == [
        RuntimeIssue(
            kind="console.error",
            url="http://frontend.local/projects",
            detail="boom",
        )
    ]


def test_unhandled_rejection_console_error_is_classified_separately() -> None:
    gate = FrontendCrashGate()
    page = FakePage(url="http://frontend.local/editors/tiptap?id=123")
    gate.attach(page)

    console_handler = page.handlers["console"]
    console_handler(
        FakeConsoleMessage(
            type="error",
            text="[e2e-unhandledrejection] TypeError: Cannot read properties of undefined",
        )
    )

    issues = gate._issues  # noqa: SLF001 - verify test-only runtime gate behavior
    assert issues == [
        RuntimeIssue(
            kind="unhandledrejection",
            url="http://frontend.local/editors/tiptap?id=123",
            detail="[e2e-unhandledrejection] TypeError: Cannot read properties of undefined",
        )
    ]


def test_request_failure_text_reads_playwright_style_dict() -> None:
    request = FakeRequest(
        url="http://frontend.local/api/projects",
        failure={"errorText": "net::ERR_CONNECTION_REFUSED"},
    )

    assert _request_failure_text(request) == "net::ERR_CONNECTION_REFUSED"


def test_requestfailed_records_non_aborted_failures() -> None:
    gate = FrontendCrashGate()
    page = FakePage()
    gate.attach(page)

    request_handler = page.handlers["requestfailed"]
    request_handler(
        FakeRequest(
            url="http://frontend.local/api/projects",
            method="POST",
            failure={"errorText": "net::ERR_CONNECTION_REFUSED"},
        )
    )

    issues = gate._issues  # noqa: SLF001 - verify test-only runtime gate behavior
    assert issues == [
        RuntimeIssue(
            kind="requestfailed",
            url="http://frontend.local/api/projects",
            detail=(
                "POST http://frontend.local/api/projects failed: "
                "net::ERR_CONNECTION_REFUSED"
            ),
        )
    ]


@pytest.mark.parametrize("failure_text", ["net::ERR_ABORTED", "NS_BINDING_ABORTED"])
def test_requestfailed_ignores_aborted_requests(failure_text: str) -> None:
    gate = FrontendCrashGate()
    page = FakePage()
    gate.attach(page)

    request_handler = page.handlers["requestfailed"]
    request_handler(
        FakeRequest(
            url="http://frontend.local/projects",
            failure={"errorText": failure_text},
        )
    )

    assert gate._issues == []  # noqa: SLF001 - verify test-only runtime gate behavior


def test_pageerror_is_recorded() -> None:
    gate = FrontendCrashGate()
    page = FakePage()
    gate.attach(page)

    pageerror_handler = page.handlers["pageerror"]
    pageerror_handler(RuntimeError("render exploded"))

    issues = gate._issues  # noqa: SLF001 - verify test-only runtime gate behavior
    assert issues == [
        RuntimeIssue(
            kind="pageerror",
            url="http://frontend.local/projects",
            detail="render exploded",
        )
    ]


def test_assert_clean_passes_without_issues() -> None:
    gate = FrontendCrashGate()

    gate.assert_clean(test_id="tests/e2e/test_login_e2e.py::test_login_flow")


def test_assert_clean_fails_with_first_and_additional_issues() -> None:
    gate = FrontendCrashGate()
    gate._issues.extend(  # noqa: SLF001 - verify failure output format
        [
            RuntimeIssue(
                kind="console.error",
                url="http://frontend.local/projects",
                detail="first boom",
            ),
            RuntimeIssue(
                kind="requestfailed",
                url="http://frontend.local/api/projects",
                detail="GET http://frontend.local/api/projects failed: timeout",
            ),
        ]
    )

    with pytest.raises(pytest.fail.Exception) as excinfo:
        gate.assert_clean(test_id="tests/e2e/test_login_e2e.py::test_login_flow")

    message = str(excinfo.value)
    assert "Frontend runtime crash gate failed" in message
    assert "First issue: console.error at http://frontend.local/projects" in message
    assert "Detail: first boom" in message
    assert "Additional issues:" in message
    assert "- requestfailed at http://frontend.local/api/projects" in message
