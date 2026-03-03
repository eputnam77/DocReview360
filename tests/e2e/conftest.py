import importlib.util
import json
import os
import sys
import types
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

playwright_spec = importlib.util.find_spec("playwright")
sync_api_spec = importlib.util.find_spec("playwright.sync_api") if playwright_spec else None

if sync_api_spec is None:
    sync_playwright = None
    if "playwright.sync_api" not in sys.modules:
        stub_module = types.ModuleType("playwright.sync_api")

        class Page:  # noqa: D401 - simple stub for type imports
            """Stub Playwright Page."""

        stub_module.Page = Page
        sys.modules["playwright.sync_api"] = stub_module
        if "playwright" not in sys.modules:
            root_module = types.ModuleType("playwright")
            root_module.sync_api = stub_module
            sys.modules["playwright"] = root_module
else:
    from playwright.sync_api import sync_playwright


def _playwright_ready() -> tuple[bool, str]:
    if sync_playwright is None:
        return False, "playwright not installed"
    try:
        with sync_playwright() as pw:
            chrome = Path(pw.chromium.executable_path)
            if not chrome.exists():
                return False, "playwright browsers not installed"
    except Exception as exc:  # noqa: BLE001 - surface skip reason in constrained envs
        return False, f"playwright unavailable: {exc}"
    return True, ""


def pytest_configure(config: pytest.Config) -> None:
    ready, reason = _playwright_ready()
    if not ready and os.getenv("E2E_REQUIRE_PLAYWRIGHT") == "1":
        raise pytest.UsageError(f"Playwright required but unavailable: {reason}")
    config._playwright_ready = ready
    config._playwright_skip_reason = reason


def pytest_report_header(config: pytest.Config) -> str | None:
    if getattr(config, "_playwright_ready", True):
        return None
    reason = getattr(config, "_playwright_skip_reason", "playwright not installed")
    return f"E2E Playwright disabled: {reason}"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if getattr(config, "_playwright_ready", True):
        return
    reason = getattr(config, "_playwright_skip_reason", "playwright not installed")
    skip_marker = pytest.mark.skip(reason=reason)
    e2e_marks = {"e2e", "e2e_smoke", "e2e_full"}
    e2e_dir = Path(__file__).parent
    for item in items:
        item_path = Path(item.fspath)
        item_marks = {m.name for m in item.iter_markers()}
        if item_path.is_relative_to(e2e_dir) or item_marks & e2e_marks:
            item.add_marker(skip_marker)


@pytest.fixture(autouse=True)
def _configure_e2e_browser_runtime(page, e2e_backend_url: str) -> None:
    """Set runtime API base and reduce Next.js overlay interaction issues."""
    backend_literal = json.dumps(e2e_backend_url)
    page.add_init_script(
        f"""
        () => {{
          const backendUrl = {backend_literal};
          window.__DOCREVIEW360_API_BASE = backendUrl;
          try {{
            localStorage.setItem("docreview360_api_base", backendUrl);
          }} catch (_) {{
            // ignore storage restrictions in constrained contexts
          }}
          const inject = () => {{
            if (document.getElementById("__e2e_disable_nextjs_portal_pointer")) {{
              return;
            }}
            const style = document.createElement("style");
            style.id = "__e2e_disable_nextjs_portal_pointer";
            style.textContent = "nextjs-portal {{ pointer-events: none !important; }}";
            (document.head || document.documentElement).appendChild(style);
          }};
          inject();
          new MutationObserver(() => inject()).observe(document.documentElement, {{
            childList: true,
            subtree: true,
          }});
        }}
        """,
    )


@pytest.fixture(scope="session")
def e2e_backend_url() -> str:
    backend = os.getenv("E2E_BACKEND_URL")
    if not backend:
        pytest.skip("E2E_BACKEND_URL not set; run scripts/run_e2e.py", allow_module_level=True)
    return backend.rstrip("/")


@pytest.fixture(scope="session")
def e2e_frontend_url() -> str:
    frontend = os.getenv("E2E_FRONTEND_URL")
    if not frontend:
        pytest.skip("E2E_FRONTEND_URL not set; run scripts/run_e2e.py", allow_module_level=True)
    return frontend.rstrip("/")


@pytest.fixture(scope="session")
def e2e_seed_data(e2e_backend_url: str) -> dict:
    req = Request(f"{e2e_backend_url}/e2e/seed", method="POST")
    with urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload
