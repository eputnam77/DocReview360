from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ["DOCREVIEW360_ENV"] = "dev"
os.environ["DOCREVIEW360_RBAC_DB"] = "/tmp/docreview360-import-roles.db"
os.environ["DOCREVIEW360_USER_DB"] = "/tmp/docreview360-import-users.db"
os.environ["DOCREVIEW360_SEARCH_DB"] = "/tmp/docreview360-import-search.db"
os.environ["DOCREVIEW360_DATABASE_URL"] = "sqlite:////tmp/docreview360-import-app.db"

from docreview360 import audit, auth, db_store, rbac, reporting, search
from docreview360.approvals import approvals
from docreview360.review_assignments import create_assignment
from docreview360.search import ProjectModel, add_project
from docreview360.workflows import workflows

REPO_ROOT = Path(__file__).resolve().parents[1]


def _project_file(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path) -> None:
    auth.configure_user_repository(tmp_path / "users.db")
    rbac.configure_role_repository(tmp_path / "roles.db")
    audit._AUDIT_LOG_PATH = tmp_path / "audit.log"
    audit._AUDIT_ANCHOR_PATH = tmp_path / "audit.anchor"
    rbac.reset_role_assignments(include_defaults=False)
    db_store.reset_db(f"sqlite:///{tmp_path / 'app.db'}")
    search._reset_state_for_testing(db_path=tmp_path / "search.db")
    approvals.clear()
    workflows.clear()
    reporting.reset_metrics_for_testing()
    yield
    approvals.clear()
    workflows.clear()
    search._reset_state_for_testing(db_path=tmp_path / "search.db")
    db_store.reset_db(None)


def test_assignment_only_reviewer_is_scoped_into_projects_and_dashboard() -> None:
    add_project(ProjectModel(id="p-review", name="Assignment Only"))
    create_assignment("p-review", "bob", status="invited")

    scoped_projects = search.list_projects("bob")
    assert [project.id for project in scoped_projects] == ["p-review"]

    dashboard_entries = reporting.dashboard_data("bob")
    assert [entry.id for entry in dashboard_entries] == ["p-review"]

    widgets = reporting.widget_counts("bob")
    assert widgets.assigned == 1
    assert widgets.pending_approvals == 1


def test_translation_hook_has_public_locale_fallback_for_logged_out_pages() -> None:
    hook_source = _project_file("frontend/lib/useTranslation.ts")
    assert "/locales/" in hook_source
    assert "common.json" in hook_source
    assert "_loadPublicLocaleStrings" in hook_source


def test_admin_dashboard_reads_audit_feed_and_uses_permissions_copy() -> None:
    admin_dashboard = _project_file("frontend/pages/dashboard/admin.tsx")
    assert "/api/audit" in admin_dashboard
    assert "permissions" in admin_dashboard
    assert "perms" not in admin_dashboard


def test_project_approval_picker_accepts_invited_reviewers() -> None:
    project_page = _project_file("frontend/pages/projects/[id]/index.tsx")
    assert "approvalReviewerOptions" in project_page
    assert (
        "Invite the reviewer in the Reviewers section before adding a phase approval."
        in project_page
    )


def test_checker_uses_public_documents_fallback_and_descriptive_labels() -> None:
    checker_page = _project_file("frontend/pages/tools/checker.tsx")
    assert "/documents/public" in checker_page
    assert "Showing public system documents only." in checker_page
    assert "formatSystemDocumentLabel" in checker_page


def test_tiptap_editor_uses_safe_indent_commands_and_larger_canvas() -> None:
    tiptap_page = _project_file("frontend/pages/editors/tiptap.tsx")
    assert 'runEditorCommand(editor, "indent")' in tiptap_page
    assert 'canRunEditorCommand(editor, "indent")' in tiptap_page
    assert 'max-w-[1200px]' in tiptap_page
    assert 'min-h-[calc(100vh-12rem)]' in tiptap_page



def test_tiptap_styles_restore_visible_list_markers_and_indentation() -> None:
    tiptap_styles = _project_file("frontend/styles/tiptap.css")
    assert 'list-style-type: disc' in tiptap_styles
    assert 'list-style-type: decimal' in tiptap_styles
    assert '[data-indent="1"]' in tiptap_styles
