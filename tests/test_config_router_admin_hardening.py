from __future__ import annotations

from datetime import timedelta

from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient


def _headers(username: str, roles: list[str]) -> dict[str, str]:
    repo = auth._get_user_repository()
    if repo.get_user(username) is None:
        repo.create_user(username, "Password!1Secure")
    rbac.set_user_roles(username, roles)
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _admin_headers() -> dict[str, str]:
    return _headers("config-admin", ["admin"])


def _user_headers() -> dict[str, str]:
    return _headers("config-user", ["user"])


def test_project_config_writes_require_admin() -> None:
    client = TestClient(app)
    user_headers = _user_headers()

    denied = client.put(
        "/config/project/proj-1/ui.items_per_page",
        json={"value": 99},
        headers=user_headers,
    )
    assert denied.status_code == 403

    read_back = client.get("/config/project/proj-1", headers=user_headers)
    assert read_back.status_code == 200
    assert read_back.json()["ui.items_per_page"] == 25

    admin_headers = _admin_headers()
    updated = client.put(
        "/config/project/proj-1/ui.items_per_page",
        json={"value": 10},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == 10

    deleted = client.delete(
        "/config/project/proj-1/ui.items_per_page",
        headers=admin_headers,
    )
    assert deleted.status_code == 200


def test_document_custom_field_value_writes_require_admin() -> None:
    client = TestClient(app)
    admin_headers = _admin_headers()
    create_field = client.post(
        "/orgs/org-hardening/fields",
        json={
            "entity_type": "document",
            "field_name": "classification",
            "field_label": "Classification",
            "field_type": "text",
        },
        headers=admin_headers,
    )
    assert create_field.status_code == 200

    denied = client.put(
        "/documents/doc-hardening/custom-fields?org_id=org-hardening",
        json={"classification": "CUI"},
        headers=_user_headers(),
    )
    assert denied.status_code == 403

    updated = client.put(
        "/documents/doc-hardening/custom-fields?org_id=org-hardening",
        json={"classification": "CUI"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["updated"] == ["classification"]

    read_back = client.get(
        "/documents/doc-hardening/custom-fields?org_id=org-hardening",
        headers=_user_headers(),
    )
    assert read_back.status_code == 200
    assert read_back.json()["fields"]["classification"] == "CUI"


def test_project_custom_field_value_writes_require_admin() -> None:
    client = TestClient(app)
    admin_headers = _admin_headers()
    create_field = client.post(
        "/orgs/org-hardening/fields",
        json={
            "entity_type": "project",
            "field_name": "priority",
            "field_label": "Priority",
            "field_type": "select",
            "options": ["low", "medium", "high"],
        },
        headers=admin_headers,
    )
    assert create_field.status_code == 200

    denied = client.put(
        "/projects/proj-hardening/custom-fields?org_id=org-hardening",
        json={"priority": "high"},
        headers=_user_headers(),
    )
    assert denied.status_code == 403

    updated = client.put(
        "/projects/proj-hardening/custom-fields?org_id=org-hardening",
        json={"priority": "high"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["updated"] == ["priority"]
