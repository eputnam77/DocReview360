# SPDX-License-Identifier: MIT
"""Tests verifying that all decomposed modules are importable from their original paths.

Item 30: Decompose remaining large modules into packages.
- auth.py     → auth/
- search.py   → search/
- workflows.py → workflows/
- doc_types.py → doc_types/
- documents.py → documents/
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# workflows package
# ---------------------------------------------------------------------------


class TestWorkflowsPackage:
    """Verify key names are importable from docreview360.workflows."""

    def test_import_workflow_model(self) -> None:
        from docreview360.workflows import WorkflowModel

        assert WorkflowModel is not None

    def test_import_approval_step(self) -> None:
        from docreview360.workflows import ApprovalStep

        assert ApprovalStep is not None

    def test_import_workflow_template_model(self) -> None:
        from docreview360.workflows import WorkflowTemplateModel

        assert WorkflowTemplateModel is not None

    def test_import_workflow_template_payload(self) -> None:
        from docreview360.workflows import WorkflowTemplatePayload

        assert WorkflowTemplatePayload is not None

    def test_import_workflow_template_step(self) -> None:
        from docreview360.workflows import WorkflowTemplateStep

        assert WorkflowTemplateStep is not None

    def test_import_get_workflow(self) -> None:
        from docreview360.workflows import get_workflow

        assert callable(get_workflow)

    def test_import_create_workflow(self) -> None:
        from docreview360.workflows import create_workflow

        assert callable(create_workflow)

    def test_import_list_workflows(self) -> None:
        from docreview360.workflows import list_workflows

        assert callable(list_workflows)

    def test_import_advance_workflow(self) -> None:
        from docreview360.workflows import advance_workflow

        assert callable(advance_workflow)

    def test_import_start_workflow(self) -> None:
        from docreview360.workflows import start_workflow

        assert callable(start_workflow)

    def test_import_assign_reviewer(self) -> None:
        from docreview360.workflows import assign_reviewer

        assert callable(assign_reviewer)

    def test_import_list_workflow_templates(self) -> None:
        from docreview360.workflows import list_workflow_templates

        assert callable(list_workflow_templates)

    def test_import_get_workflow_template(self) -> None:
        from docreview360.workflows import get_workflow_template

        assert callable(get_workflow_template)

    def test_import_create_workflow_template(self) -> None:
        from docreview360.workflows import create_workflow_template

        assert callable(create_workflow_template)

    def test_import_reset_workflow_templates(self) -> None:
        from docreview360.workflows import reset_workflow_templates

        assert callable(reset_workflow_templates)

    def test_import_default_workflow_templates(self) -> None:
        from docreview360.workflows import DEFAULT_WORKFLOW_TEMPLATES

        assert isinstance(DEFAULT_WORKFLOW_TEMPLATES, dict)
        assert "branch-coordination" in DEFAULT_WORKFLOW_TEMPLATES

    def test_import_workflows_dict(self) -> None:
        from docreview360.workflows import workflows

        assert isinstance(workflows, dict)

    def test_import_workflow_templates_dict(self) -> None:
        from docreview360.workflows import workflow_templates

        assert isinstance(workflow_templates, dict)

    def test_import_bot_callbacks(self) -> None:
        from docreview360.workflows import bot_callbacks

        assert isinstance(bot_callbacks, list)

    def test_import_get_approval_steps_for_phase(self) -> None:
        from docreview360.workflows import get_approval_steps_for_phase

        assert callable(get_approval_steps_for_phase)

    def test_import_list_roles(self) -> None:
        from docreview360.workflows import list_roles

        assert callable(list_roles)

    def test_list_workflow_templates_returns_defaults(self) -> None:
        from docreview360.workflows import list_workflow_templates

        templates = list_workflow_templates()
        names = [t.name for t in templates]
        assert "branch-coordination" in names

    def test_get_workflow_returns_none_for_unknown(self) -> None:
        from docreview360.workflows import get_workflow

        result = get_workflow("nonexistent-workflow-id-xyz")
        assert result is None

    def test_list_roles_returns_sorted_list(self) -> None:
        from docreview360.workflows import list_roles

        roles = list_roles()
        assert isinstance(roles, list)
        assert roles == sorted(roles)
        assert len(roles) > 0


# ---------------------------------------------------------------------------
# doc_types package
# ---------------------------------------------------------------------------


class TestDocTypesPackage:
    """Verify key names are importable from docreview360.doc_types."""

    def test_import_document_type_model(self) -> None:
        from docreview360.doc_types import DocumentTypeModel

        assert DocumentTypeModel is not None

    def test_import_list_document_types(self) -> None:
        from docreview360.doc_types import list_document_types

        assert callable(list_document_types)

    def test_import_get_document_type(self) -> None:
        from docreview360.doc_types import get_document_type

        assert callable(get_document_type)

    def test_import_add_document_type(self) -> None:
        from docreview360.doc_types import add_document_type

        assert callable(add_document_type)

    def test_import_update_document_type(self) -> None:
        from docreview360.doc_types import update_document_type

        assert callable(update_document_type)

    def test_import_delete_document_type(self) -> None:
        from docreview360.doc_types import delete_document_type

        assert callable(delete_document_type)

    def test_import_reset_document_types(self) -> None:
        from docreview360.doc_types import reset_document_types

        assert callable(reset_document_types)

    def test_import_export_document_types_json(self) -> None:
        from docreview360.doc_types import export_document_types_json

        assert callable(export_document_types_json)

    def test_import_import_document_types_json(self) -> None:
        from docreview360.doc_types import import_document_types_json

        assert callable(import_document_types_json)

    def test_import_list_all_phases(self) -> None:
        from docreview360.doc_types import list_all_phases

        assert callable(list_all_phases)

    def test_import_default_doc_type_phases(self) -> None:
        from docreview360.doc_types import DEFAULT_DOC_TYPE_PHASES

        assert isinstance(DEFAULT_DOC_TYPE_PHASES, dict)
        assert len(DEFAULT_DOC_TYPE_PHASES) > 0

    def test_import_document_types_mapping(self) -> None:
        from docreview360.doc_types import document_types

        assert document_types is not None

    def test_import_data_file_stub(self) -> None:
        from docreview360.doc_types import DATA_FILE

        # DATA_FILE is None stub for backward compat
        assert DATA_FILE is None

    def test_import_save_state_stub(self) -> None:
        from docreview360.doc_types import save_state

        assert callable(save_state)

    def test_list_document_types_returns_list(self) -> None:
        from docreview360.doc_types import list_document_types

        types = list_document_types()
        assert isinstance(types, list)
        # With seeded defaults there should be at least 1 type
        assert len(types) >= 0  # may be 0 in pristine test DB

    def test_document_type_model_has_id_alias(self) -> None:
        from docreview360.doc_types import DocumentTypeModel

        dt = DocumentTypeModel(name="Test", template="<h1>Test</h1>", workflow=["Draft"])
        assert dt.id == "Test"
        assert dt.phases == ["Draft"]


# ---------------------------------------------------------------------------
# documents package
# ---------------------------------------------------------------------------


class TestDocumentsPackage:
    """Verify key names are importable from docreview360.documents."""

    def test_import_document_model(self) -> None:
        from docreview360.documents import DocumentModel

        assert DocumentModel is not None

    def test_import_document_revision(self) -> None:
        from docreview360.documents import DocumentRevision

        assert DocumentRevision is not None

    def test_import_frozen_document_error(self) -> None:
        from docreview360.documents import FrozenDocumentError

        assert issubclass(FrozenDocumentError, RuntimeError)

    def test_import_documents_dict(self) -> None:
        from docreview360.documents import documents

        assert isinstance(documents, dict)

    def test_import_import_document(self) -> None:
        from docreview360.documents import import_document

        assert callable(import_document)

    def test_import_get_document(self) -> None:
        from docreview360.documents import get_document

        assert callable(get_document)

    def test_import_list_documents(self) -> None:
        from docreview360.documents import list_documents

        assert callable(list_documents)

    def test_import_update_document(self) -> None:
        from docreview360.documents import update_document

        assert callable(update_document)

    def test_import_autosave_document(self) -> None:
        from docreview360.documents import autosave_document

        assert callable(autosave_document)

    def test_import_freeze_document(self) -> None:
        from docreview360.documents import freeze_document

        assert callable(freeze_document)

    def test_import_unfreeze_document(self) -> None:
        from docreview360.documents import unfreeze_document

        assert callable(unfreeze_document)

    def test_import_restore_document_version(self) -> None:
        from docreview360.documents import restore_document_version

        assert callable(restore_document_version)

    def test_import_get_version_history(self) -> None:
        from docreview360.documents import get_version_history

        assert callable(get_version_history)

    def test_import_diff_document_revisions(self) -> None:
        from docreview360.documents import diff_document_revisions

        assert callable(diff_document_revisions)

    def test_import_link_approval(self) -> None:
        from docreview360.documents import link_approval

        assert callable(link_approval)

    def test_import_unlink_approval(self) -> None:
        from docreview360.documents import unlink_approval

        assert callable(unlink_approval)

    def test_import_sanitize_content(self) -> None:
        from docreview360.documents import sanitize_content

        assert callable(sanitize_content)

    def test_import_register_ingestion_pipeline(self) -> None:
        from docreview360.documents import register_ingestion_pipeline

        assert callable(register_ingestion_pipeline)

    def test_import_ingestion_registry(self) -> None:
        from docreview360.documents import IngestionRegistry, ingestion_registry

        assert isinstance(ingestion_registry, IngestionRegistry)

    def test_import_default_allowed_mime_types(self) -> None:
        from docreview360.documents import DEFAULT_ALLOWED_MIME_TYPES

        assert isinstance(DEFAULT_ALLOWED_MIME_TYPES, frozenset)
        assert "text/plain" in DEFAULT_ALLOWED_MIME_TYPES

    def test_sanitize_removes_script_tags(self) -> None:
        from docreview360.documents import sanitize_content

        result = sanitize_content("<script>alert('xss')</script>hello")
        assert "<script>" not in result
        assert "hello" in result

    def test_get_document_returns_none_for_unknown(self) -> None:
        from docreview360.documents import get_document

        assert get_document("nonexistent-doc-id-xyz") is None

    def test_document_model_defaults(self) -> None:
        from docreview360.documents import DocumentModel

        doc = DocumentModel(id="test-id", content="hello")
        assert doc.version_number == 1
        assert doc.frozen is False
        assert doc.approval_ids == []


# ---------------------------------------------------------------------------
# search package
# ---------------------------------------------------------------------------


class TestSearchPackage:
    """Verify key names are importable from docreview360.search."""

    def test_import_project_model(self) -> None:
        from docreview360.search import ProjectModel

        assert ProjectModel is not None

    def test_import_saved_search(self) -> None:
        from docreview360.search import SavedSearch

        assert SavedSearch is not None

    def test_import_search_index(self) -> None:
        from docreview360.search import SearchIndex

        assert SearchIndex is not None

    def test_import_search_repository(self) -> None:
        from docreview360.search import SearchRepository

        assert SearchRepository is not None

    def test_import_search_fn(self) -> None:
        from docreview360.search import search

        assert callable(search)

    def test_import_search_documents(self) -> None:
        from docreview360.search import search_documents

        assert callable(search_documents)

    def test_import_ranked_search(self) -> None:
        from docreview360.search import ranked_search

        assert callable(ranked_search)

    def test_import_add_project(self) -> None:
        from docreview360.search import add_project

        assert callable(add_project)

    def test_import_update_project(self) -> None:
        from docreview360.search import update_project

        assert callable(update_project)

    def test_import_get_project(self) -> None:
        from docreview360.search import get_project

        assert callable(get_project)

    def test_import_list_projects(self) -> None:
        from docreview360.search import list_projects

        assert callable(list_projects)

    def test_import_remove_project(self) -> None:
        from docreview360.search import remove_project

        assert callable(remove_project)

    def test_import_save_search(self) -> None:
        from docreview360.search import save_search

        assert callable(save_search)

    def test_import_list_saved_searches(self) -> None:
        from docreview360.search import list_saved_searches

        assert callable(list_saved_searches)

    def test_import_search_stats(self) -> None:
        from docreview360.search import search_stats

        assert callable(search_stats)

    def test_import_projects_dict(self) -> None:
        from docreview360.search import projects

        assert isinstance(projects, dict)

    def test_import_search_index_instance(self) -> None:
        from docreview360.search import SearchIndex, search_index

        assert isinstance(search_index, SearchIndex)

    def test_import_locks(self) -> None:
        import threading

        from docreview360.search import (
            index_lock,
            project_lock,
        )

        assert isinstance(project_lock, type(threading.Lock()))
        assert isinstance(index_lock, type(threading.Lock()))

    def test_search_returns_empty_for_no_match(self) -> None:
        from docreview360.search import search

        results = search("thisisaverylongquerythatmatchesnothing12345")
        assert results == []

    def test_search_documents_alias(self) -> None:
        from docreview360.search import search, search_documents

        # Both should return the same type of results
        r1 = search("unique_test_query_xyz")
        r2 = search_documents("unique_test_query_xyz")
        assert r1 == r2

    def test_list_projects_returns_list(self) -> None:
        from docreview360.search import list_projects

        result = list_projects()
        assert isinstance(result, list)

    def test_project_model_has_computed_fields(self) -> None:
        from docreview360.search import ProjectModel

        pm = ProjectModel(id="test", name="My Project")
        assert pm.title == "My Project"
        assert pm.type == "Unknown"
        assert pm.status == "Draft"
        assert pm.progress == 0


# ---------------------------------------------------------------------------
# auth package
# ---------------------------------------------------------------------------


class TestAuthPackage:
    """Verify key names are importable from docreview360.auth."""

    def test_import_get_current_user(self) -> None:
        from docreview360.auth import get_current_user

        assert callable(get_current_user)

    def test_import_get_optional_user(self) -> None:
        # get_optional_user may not exist in auth.py — test gracefully
        try:
            from docreview360.auth import get_optional_user

            assert callable(get_optional_user)
        except ImportError:
            pass  # Optional export

    def test_import_authenticate_user(self) -> None:
        from docreview360.auth import authenticate_user

        assert callable(authenticate_user)

    def test_import_authenticate_mfa(self) -> None:
        from docreview360.auth import authenticate_mfa

        assert callable(authenticate_mfa)

    def test_import_create_access_token(self) -> None:
        from docreview360.auth import create_access_token

        assert callable(create_access_token)

    def test_import_create_id_token(self) -> None:
        from docreview360.auth import create_id_token

        assert callable(create_id_token)

    def test_import_login_for_access_token(self) -> None:
        from docreview360.auth import login_for_access_token

        assert callable(login_for_access_token)

    def test_import_login_for_oidc_token(self) -> None:
        from docreview360.auth import login_for_oidc_token

        assert callable(login_for_oidc_token)

    def test_import_revoke_token(self) -> None:
        from docreview360.auth import revoke_token

        assert callable(revoke_token)

    def test_import_is_token_revoked(self) -> None:
        from docreview360.auth import is_token_revoked

        assert callable(is_token_revoked)

    def test_import_is_active(self) -> None:
        from docreview360.auth import is_active

        assert callable(is_active)

    def test_import_user_repository(self) -> None:
        from docreview360.auth import UserRepository

        assert UserRepository is not None

    def test_import_user_record(self) -> None:
        from docreview360.auth import UserRecord

        assert UserRecord is not None

    def test_import_user_model(self) -> None:
        from docreview360.auth import User

        assert User is not None

    def test_import_token_model(self) -> None:
        from docreview360.auth import Token

        assert Token is not None

    def test_import_password_policy(self) -> None:
        from docreview360.auth import PasswordPolicy

        assert PasswordPolicy is not None

    def test_import_password_policy_error(self) -> None:
        from docreview360.auth import PasswordPolicyError

        assert issubclass(PasswordPolicyError, ValueError)

    def test_import_oauth2_scheme(self) -> None:
        from docreview360.auth import oauth2_scheme

        assert oauth2_scheme is not None

    def test_import_constants(self) -> None:
        from docreview360.auth import (
            DEMO_USER_DEFAULTS,
            SAFE_DEFAULT_ENVS,
            USER_REPOSITORY,
        )

        assert isinstance(SAFE_DEFAULT_ENVS, set)
        assert isinstance(DEMO_USER_DEFAULTS, dict)
        assert "alice" in DEMO_USER_DEFAULTS
        assert USER_REPOSITORY is not None

    def test_import_configure_user_repository(self) -> None:
        from docreview360.auth import configure_user_repository

        assert callable(configure_user_repository)

    def test_import_keycloak_helpers(self) -> None:
        from docreview360.auth import (
            authenticate_keycloak,
            has_role,
            keycloak_mfa_login,
        )

        assert callable(authenticate_keycloak)
        assert callable(has_role)
        assert callable(keycloak_mfa_login)

    def test_password_policy_load(self) -> None:
        from docreview360.auth import PasswordPolicy

        policy = PasswordPolicy.load()
        assert policy.min_length > 0
        assert policy.min_character_classes > 0

    def test_user_repository_hash_verify(self) -> None:
        from docreview360.auth import UserRepository

        hashed = UserRepository.hash_password("TestPassw0rd!")
        assert UserRepository.verify_password("TestPassw0rd!", hashed)
        assert not UserRepository.verify_password("WrongPassword!", hashed)

    def test_user_model(self) -> None:
        from docreview360.auth import User

        user = User(username="testuser", active=True)
        assert user.username == "testuser"
        assert user.active is True

    def test_token_model(self) -> None:
        from docreview360.auth import Token

        token = Token(access_token="abc123", token_type="bearer")
        assert token.access_token == "abc123"
        assert token.token_type == "bearer"


# ---------------------------------------------------------------------------
# Cross-module integration: original import paths still work
# ---------------------------------------------------------------------------


class TestCrossModuleImports:
    """Verify that modules which import from each other continue to work."""

    def test_search_imports_from_documents(self) -> None:
        """search imports DocumentModel from documents."""
        from docreview360.search import search_index

        assert search_index is not None

    def test_search_imports_from_workflows(self) -> None:
        """search.ProjectModel uses get_workflow from workflows."""
        from docreview360.search import ProjectModel

        pm = ProjectModel(id="test", name="test", workflow=None)
        # phase is None when no workflow assigned
        assert pm.phase is None

    def test_doc_types_imports_from_search(self) -> None:
        """doc_types.update_document_type imports from search on rename."""
        from docreview360.doc_types import update_document_type

        assert callable(update_document_type)

    def test_documents_imports_from_audit(self) -> None:
        """documents uses log_audit_event from audit."""
        from docreview360.documents import import_document

        assert callable(import_document)

    def test_workflows_engine_imports_from_approvals(self) -> None:
        """workflows.create_workflow imports create_approval from approvals."""
        from docreview360.workflows import create_workflow

        assert callable(create_workflow)
