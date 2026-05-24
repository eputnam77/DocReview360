import json
import re
from uuid import uuid4

import pytest
from playwright.sync_api import Page

from .test_project_profile_e2e import _auth_headers, _login

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_smoke]


def _first_doc_type_and_phase(page: Page, backend_url: str, headers: dict[str, str]) -> tuple[str, str]:  # noqa: E501
    doc_types_resp = page.request.get(f"{backend_url}/document-types", headers=headers)
    assert doc_types_resp.ok
    doc_types = doc_types_resp.json()
    assert isinstance(doc_types, list) and doc_types
    selected = doc_types[0]
    phases = selected.get("phases") or selected.get("workflow") or []
    assert phases, "Expected backend document type to include phases"
    return selected["name"], phases[0]


def _create_project(
    page: Page,
    backend_url: str,
    headers: dict[str, str],
    *,
    name: str,
    document_number: str,
    doc_type: str,
    phase: str,
) -> str:
    resp = page.request.post(
        f"{backend_url}/projects",
        headers=headers,
        data={
            "name": name,
            "document_number": document_number,
            "doc_type": doc_type,
            "phase": phase,
            "user": "bob",
        },
    )
    assert resp.status == 201
    return resp.json()["id"]


def test_project_edit_document_route_follows_editor_config(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    headers = _auth_headers(page)
    config_resp = page.request.get(f"{e2e_backend_url}/config", headers=headers)
    assert config_resp.ok
    original_config = config_resp.json()
    doc_type_name, selected_phase = _first_doc_type_and_phase(page, e2e_backend_url, headers)

    def update_editor(editor: str) -> None:
        payload = dict(original_config)
        payload["editor"] = editor
        resp = page.request.put(
            f"{e2e_backend_url}/config",
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps(payload),
        )
        assert resp.ok, resp.text()

    try:
        update_editor("ckeditor5")
        ck_project_id = _create_project(
            page,
            e2e_backend_url,
            headers,
            name=f"E2E CKEditor Route {uuid4().hex[:8]}",
            document_number=f"E2E-CKE-{uuid4().hex[:6]}",
            doc_type=doc_type_name,
            phase=selected_phase,
        )
        page.goto(f"{e2e_frontend_url}/projects/{ck_project_id}")
        cke_link = page.get_by_role("link", name=re.compile(r"edit document", re.I)).first
        cke_link.wait_for()
        cke_href = cke_link.get_attribute("href")
        assert cke_href == f"/editors/ckeditor5?projectId={ck_project_id}"
        cke_link.click(force=True)
        page.wait_for_url(re.compile(rf"{re.escape(e2e_frontend_url)}/editors/ckeditor5\?projectId={re.escape(ck_project_id)}"))

        update_editor("tiptap")
        tt_project_id = _create_project(
            page,
            e2e_backend_url,
            headers,
            name=f"E2E TipTap Route {uuid4().hex[:8]}",
            document_number=f"E2E-TT-{uuid4().hex[:6]}",
            doc_type=doc_type_name,
            phase=selected_phase,
        )
        page.goto(f"{e2e_frontend_url}/projects/{tt_project_id}")
        tiptap_link = page.get_by_role("link", name=re.compile(r"edit document", re.I)).first
        tiptap_link.wait_for()
        tiptap_href = tiptap_link.get_attribute("href")
        assert tiptap_href == f"/editors/tiptap?projectId={tt_project_id}"
    finally:
        restore_resp = page.request.put(
            f"{e2e_backend_url}/config",
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps(original_config),
        )
        assert restore_resp.ok, restore_resp.text()
