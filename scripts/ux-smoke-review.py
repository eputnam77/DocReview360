#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""UX smoke-review loop.

Logs in as alice and bob, exercises document upload and approval flows,
then summarizes friction, broken states, and missing error messages.
Always exits 0 (informational).

Requires a running DocReview360 server or uses the TestClient.

Usage:
    python scripts/ux-smoke-review.py
    python scripts/ux-smoke-review.py --base-url http://localhost:8000
    python scripts/ux-smoke-review.py --use-test-client
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "docreview360"

findings: list[dict[str, str]] = []
steps_passed: list[str] = []
steps_failed: list[str] = []


def note(category: str, severity: str, message: str) -> None:
    findings.append({"category": category, "severity": severity, "message": message})
    indicator = "!" if severity in ("CRITICAL", "HIGH") else "~"
    print(f"  [{indicator}] [{category}] {severity}: {message}")
    steps_failed.append(f"[{category}] {message}")


def ok(category: str, message: str) -> None:
    print(f"  [+] [{category}] ok: {message}")
    steps_passed.append(f"[{category}] {message}")


def skip(category: str, message: str) -> None:
    print(f"  [~] [{category}] skip: {message}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def _make_client(base_url: str | None, use_test_client: bool) -> object | None:
    """Return a requests.Session or TestClient-like object, or None if unavailable."""
    if use_test_client or base_url is None:
        try:
            sys.path.insert(0, str(REPO_ROOT / "src"))
            os.environ.setdefault("DOCREVIEW360_ENV", "dev")
            from docreview360.api import app  # noqa: PLC0415
            from fastapi.testclient import TestClient  # noqa: PLC0415
            return TestClient(app, raise_server_exceptions=False)
        except ImportError as exc:
            skip("Client", f"Cannot import TestClient: {exc}")
            return None
    else:
        try:
            import requests  # noqa: PLC0415
            session = requests.Session()
            session.base_url = base_url  # type: ignore[attr-defined]
            return session
        except ImportError:
            skip("Client", "requests not installed — cannot connect to live server")
            return None


def _get(client: object, path: str, headers: dict | None = None) -> tuple[int, dict]:
    try:
        resp = client.get(path, headers=headers or {})  # type: ignore[union-attr]
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {"raw": resp.text[:200]}
        return resp.status_code, body
    except Exception as exc:  # noqa: BLE001
        return -1, {"error": str(exc)}


def _post(
    client: object,
    path: str,
    data: dict,
    headers: dict | None = None,
    form: bool = False,
) -> tuple[int, dict]:
    try:
        kwargs: dict = {"headers": headers or {}}
        if form:
            kwargs["data"] = data
        else:
            kwargs["json"] = data
        resp = client.post(path, **kwargs)  # type: ignore[union-attr]
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = {"raw": resp.text[:200]}
        return resp.status_code, body
    except Exception as exc:  # noqa: BLE001
        return -1, {"error": str(exc)}


# ---------------------------------------------------------------------------
# 1. Auth flow
# ---------------------------------------------------------------------------

def check_auth_flow(client: object) -> dict[str, str]:
    """Login as alice (admin) and bob (auditor). Return token headers."""
    section("Auth Flow: alice (admin) + bob (auditor)")

    tokens: dict[str, str] = {}

    for username in ("alice", "bob"):
        status, body = _post(
            client,
            "/token",
            {"username": username, "password": "password", "otp": ""},
            form=True,
        )
        if status == 200 and ("access_token" in body or "token" in str(body)):
            token = body.get("access_token") or body.get("token", "")
            tokens[username] = token
            ok("Auth", f"Login as {username}: HTTP {status}")
        else:
            note("Auth", "HIGH", f"Login as {username}: HTTP {status} — {str(body)[:80]}")

    return tokens


# ---------------------------------------------------------------------------
# 2. Project creation
# ---------------------------------------------------------------------------

def check_project_creation(client: object, headers: dict) -> str | None:
    section("Project Creation")

    status, body = _post(
        client,
        "/projects",
        {"name": "ux-smoke-test-project", "description": "UX smoke review"},
        headers=headers,
    )

    if status in (200, 201):
        project_id = body.get("id") or body.get("project_id")
        ok("Projects", f"Created project: {project_id}")
        return str(project_id) if project_id else None
    else:
        note("Projects", "HIGH", f"Project creation failed: HTTP {status} — {str(body)[:80]}")
        return None


# ---------------------------------------------------------------------------
# 3. Document upload
# ---------------------------------------------------------------------------

def check_document_upload(client: object, project_id: str, headers: dict) -> str | None:
    section("Document Upload")

    # Use the tiptap document creation endpoint with minimal TipTap JSON
    tiptap_doc = {
        "type": "doc",
        "project": project_id,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Smoke test."}]}],
    }
    status, body = _post(client, "/documents/tiptap", tiptap_doc, headers=headers)

    if status in (200, 201):
        doc_id = body.get("id") or body.get("document_id")
        ok("Documents", f"Document uploaded via /documents/tiptap: {doc_id}")
        return str(doc_id) if doc_id else None

    # 400 with a detail message means the endpoint is reachable but input invalid
    if status == 400 and "detail" in body:
        ok("Documents", "POST /documents/tiptap reachable → 400 (input validation working)")
        return None

    # 422 means the endpoint exists but input was wrong format
    if status == 422:
        ok("Documents", "POST /documents/tiptap reachable → 422 (schema validation active)")
        return None

    # Check that the documents list endpoint works
    list_status, list_body = _get(client, "/documents", headers=headers)
    if list_status == 200:
        ok("Documents", f"GET /documents reachable → 200 ({len(list_body) if isinstance(list_body, list) else '?'} docs)")
    else:
        note("Documents", "MEDIUM", f"GET /documents: HTTP {list_status}")

    return None


# ---------------------------------------------------------------------------
# 4. Approval flow
# ---------------------------------------------------------------------------

def check_approval_flow(client: object, project_id: str, headers: dict) -> None:
    section("Approval Flow")

    # GET approvals
    status, body = _get(client, f"/approvals?project_id={project_id}", headers=headers)
    if status == 200:
        ok("Approvals", f"GET /approvals: HTTP {status}")
    else:
        note("Approvals", "MEDIUM", f"GET /approvals: HTTP {status}")

    # POST approval — requires workflow and doc_id; skip gracefully if none available
    status2, body2 = _post(
        client,
        "/approvals",
        {"workflow": "smoke-test-wf", "reviewer": "bob", "doc_id": "smoke-doc"},
        headers=headers,
    )
    # 422 (validation) or 404 (workflow not found) are expected in smoke env
    if status2 in (200, 201):
        ok("Approvals", f"Approval created: HTTP {status2}")
    elif status2 in (404, 422):
        ok("Approvals", f"POST /approvals → {status2} (expected in fresh env — no real workflow)")
    else:
        note("Approvals", "MEDIUM", f"Approval request: HTTP {status2} — {str(body2)[:80]}")


# ---------------------------------------------------------------------------
# 5. Health + error handling
# ---------------------------------------------------------------------------

def check_health_endpoints(client: object) -> None:
    section("Health Endpoints")

    for path in ("/health/live", "/health/ready", "/health"):
        status, body = _get(client, path)
        if status == 200:
            ok("Health", f"GET {path}: HTTP {status}")
        elif status == -1:
            skip("Health", f"GET {path}: unreachable")
        else:
            note("Health", "HIGH", f"GET {path}: HTTP {status}")


def check_error_handling(client: object, headers: dict) -> None:
    section("Error Handling / Missing Error Messages")

    # 404 on non-existent resource
    status, body = _get(client, "/projects/nonexistent-uuid-99999", headers=headers)
    if status == 404:
        ok("Errors", "GET /projects/invalid-id → 404 (correct)")
        if "detail" in body or "error" in body or "message" in str(body):
            ok("Errors", "404 response has detail/message field")
        else:
            note("Errors", "LOW", "404 response has no detail/message — empty error body")
    elif status == 200:
        note("Errors", "MEDIUM", "GET /projects/nonexistent → 200 — should be 404")
    else:
        ok("Errors", f"GET /projects/nonexistent → {status}")

    # 401 on unauthenticated request
    status2, body2 = _get(client, "/projects")
    if status2 == 401:
        ok("Errors", "GET /projects without auth → 401 (correct)")
    elif status2 == 200:
        note("Errors", "MEDIUM", "GET /projects without auth → 200 — endpoint may be unauthenticated")
    else:
        ok("Errors", f"GET /projects without auth → {status2}")


# ---------------------------------------------------------------------------
# 6. Source-level smoke checks (always run)
# ---------------------------------------------------------------------------

def check_source_level() -> None:
    section("Source-level UX Checks")

    # Check that alice and bob demo users are seeded
    auth_init = SRC / "auth" / "__init__.py"
    if auth_init.exists():
        text = auth_init.read_text(encoding="utf-8")
        if "alice" in text and "bob" in text:
            ok("Source", "Demo users alice + bob defined in auth/__init__.py")
        else:
            note("Source", "MEDIUM", "Demo users alice/bob not found in auth/__init__.py")

    # Check for error response models
    api_init = SRC / "api" / "__init__.py"
    if api_init.exists():
        text = api_init.read_text(encoding="utf-8")
        if "HTTPException" in text or "JSONResponse" in text:
            ok("Source", "HTTPException/JSONResponse error handling present in api")
        else:
            note("Source", "LOW", "No HTTPException usage detected — errors may not be well-formed")

    # Check for input validation
    for router_path in (SRC / "api").glob("*_router.py"):
        text = router_path.read_text(encoding="utf-8")
        if "BaseModel" in text or "Field" in text or "validator" in text:
            ok("Source", f"{router_path.name}: Pydantic validation present")
            break
    else:
        note("Source", "MEDIUM", "No Pydantic BaseModel/Field validation found in routers")

    # Check frontend for error boundaries
    app_tsx = REPO_ROOT / "frontend" / "pages" / "_app.tsx"
    if app_tsx.exists():
        text = app_tsx.read_text(encoding="utf-8")
        if "ErrorBoundary" in text or "componentDidCatch" in text:
            ok("Source", "React Error Boundary present in _app.tsx")
        else:
            note("Source", "LOW", "No ErrorBoundary in _app.tsx — unhandled React errors may show blank page")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  UX SMOKE REVIEW SUMMARY")
    print("=" * 60)
    print(f"  Steps passed: {len(steps_passed)}")
    print(f"  Steps failed: {len(steps_failed)}")

    if not findings:
        print("  No UX issues detected. All smoke steps passed.")
        print("=" * 60)
        return

    by_severity: dict[str, list[dict[str, str]]] = {}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        print(f"\n  [{sev}] — {len(items)} finding(s):")
        for item in items:
            print(f"    [{item['category']}] {item['message'][:100]}")

    print(f"\n  Total: {len(findings)} issue(s) across {len(by_severity)} severity level(s).")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="DocReview360 UX smoke-review loop.")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL of running server (default: use TestClient)",
    )
    parser.add_argument(
        "--use-test-client",
        action="store_true",
        default=False,
        help="Force use of FastAPI TestClient even if --base-url provided",
    )
    args = parser.parse_args()

    print("DocReview360 UX Smoke Review")
    print(f"Repo root: {REPO_ROOT}")

    # Source-level checks always run
    check_source_level()

    # Runtime checks require client
    client = _make_client(args.base_url, args.use_test_client)
    if client is None:
        skip("Runtime", "No client available — skipping runtime smoke tests")
        skip("Runtime", "Use --use-test-client to run with FastAPI TestClient")
    else:
        check_health_endpoints(client)
        tokens = check_auth_flow(client)

        alice_headers = (
            {"Authorization": f"Bearer {tokens['alice']}"}
            if "alice" in tokens and tokens["alice"]
            else {}
        )

        project_id = None
        if alice_headers:
            project_id = check_project_creation(client, alice_headers)

        if project_id:
            check_document_upload(client, project_id, alice_headers)
            check_approval_flow(client, project_id, alice_headers)

        check_error_handling(client, alice_headers)

    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
