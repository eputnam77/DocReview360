from playwright.sync_api import Page


def _login(page: Page, frontend_url: str, backend_url: str, username: str) -> dict[str, str]:
    token_resp = page.request.post(
        f"{backend_url}/token",
        data={"username": username, "password": "password"},
    )
    assert token_resp.ok, f"Expected /token success for {username}, got {token_resp.status}"
    token_payload = token_resp.json()
    access_token = token_payload.get("access_token")
    assert access_token, "Expected access_token in /token response"
    page.goto(f"{frontend_url}/login")
    page.evaluate("(token) => localStorage.setItem('access_token', token)", access_token)
    page.wait_for_function("() => !!localStorage.getItem('access_token')")
    token = page.evaluate("() => localStorage.getItem('access_token')")
    assert token, "Expected access token in localStorage after login"
    return {"Authorization": f"Bearer {token}"}


def test_default_templates_available(page: Page, e2e_frontend_url: str, e2e_backend_url: str, e2e_seed_data) -> None:
    headers = _login(page, e2e_frontend_url, e2e_backend_url, "alice")

    templates_resp = page.request.get(f"{e2e_backend_url}/templates", headers=headers)
    assert templates_resp.ok
    templates = templates_resp.json()
    assert isinstance(templates, list) and templates
    assert any(item.get("default") is True and item.get("docType") for item in templates)

    email_resp = page.request.get(f"{e2e_backend_url}/email-templates", headers=headers)
    assert email_resp.ok
    email_templates = email_resp.json()
    names = {item.get("name") for item in email_templates if item.get("name")}
    assert {"default", "review_request", "approval_request", "signature_request", "comment_added", "project_assigned", "phase_changed", "due_reminder", "overdue_notice", "completion_notice", "review_complete", "approval_complete"}.issubset(names)
