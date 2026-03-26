# SPDX-License-Identifier: MIT
"""Tests for Item 42: hierarchical config, feature flags, custom workflows, custom fields."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# Hierarchical config tests
# ---------------------------------------------------------------------------


class TestHierarchicalConfig:
    def test_system_defaults_returned(self):
        from docreview360.db_store import get_db
        from docreview360.hierarchical_config import SYSTEM_DEFAULTS, get_config

        with get_db().orm_session() as db:
            val = get_config(db, "auth.mfa_required")
            assert val == SYSTEM_DEFAULTS["auth.mfa_required"]

    def test_org_override_takes_precedence(self):
        from docreview360.db_store import get_db
        from docreview360.hierarchical_config import get_config, set_org_config

        with get_db().orm_session() as db:
            set_org_config(db, "org-alpha", "auth.mfa_required", True, updated_by="admin")
            val = get_config(db, "auth.mfa_required", org_id="org-alpha")
            assert val is True

    def test_project_override_takes_precedence_over_org(self):
        from docreview360.db_store import get_db
        from docreview360.hierarchical_config import get_config, set_org_config, set_project_config

        with get_db().orm_session() as db:
            set_org_config(db, "org-beta", "ui.items_per_page", 50, updated_by="admin")
            set_project_config(db, "proj-beta-1", "ui.items_per_page", 10, updated_by="admin")
            val = get_config(db, "ui.items_per_page", org_id="org-beta", project_id="proj-beta-1")
            assert val == 10

    def test_system_fallback_when_no_overrides(self):
        from docreview360.db_store import get_db
        from docreview360.hierarchical_config import get_config

        with get_db().orm_session() as db:
            val = get_config(db, "notifications.email_enabled", org_id="org-unknown")
            assert val is True  # system default

    def test_unknown_key_raises_key_error(self):
        from docreview360.db_store import get_db
        from docreview360.hierarchical_config import get_config

        with get_db().orm_session() as db:
            with pytest.raises(KeyError):
                get_config(db, "this.key.does.not.exist")

    def test_delete_org_config(self):
        from docreview360.db_store import get_db
        from docreview360.hierarchical_config import delete_org_config, get_config, set_org_config

        with get_db().orm_session() as db:
            set_org_config(db, "org-gamma", "ui.items_per_page", 100, updated_by="admin")
            deleted = delete_org_config(db, "org-gamma", "ui.items_per_page")
            assert deleted is True
            # Should fall back to system default
            val = get_config(db, "ui.items_per_page", org_id="org-gamma")
            assert val == 25  # system default

    def test_get_org_config_all_merges_defaults(self):
        from docreview360.db_store import get_db
        from docreview360.hierarchical_config import (
            get_org_config_all,
            set_org_config,
        )

        with get_db().orm_session() as db:
            set_org_config(db, "org-delta", "auth.mfa_required", True, updated_by="admin")
            result = get_org_config_all(db, "org-delta")
            # Override applied
            assert result["auth.mfa_required"] is True
            # System defaults also present
            assert "ui.items_per_page" in result


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------


class TestFeatureFlags:
    def test_built_in_default_true(self):
        from docreview360.db_store import get_db
        from docreview360.feature_flags import is_flag_enabled

        with get_db().orm_session() as db:
            assert is_flag_enabled(db, "document_branches") is True

    def test_built_in_default_false(self):
        from docreview360.db_store import get_db
        from docreview360.feature_flags import is_flag_enabled

        with get_db().orm_session() as db:
            assert is_flag_enabled(db, "beta_editor") is False

    def test_org_specific_override(self):
        from docreview360.db_store import get_db
        from docreview360.feature_flags import is_flag_enabled, set_flag

        with get_db().orm_session() as db:
            set_flag(db, "beta_editor", enabled=True, org_id="org-early-adopter")
            assert is_flag_enabled(db, "beta_editor", org_id="org-early-adopter") is True
            # Other orgs unaffected
            assert is_flag_enabled(db, "beta_editor", org_id="org-other") is False

    def test_unknown_flag_returns_false(self):
        from docreview360.db_store import get_db
        from docreview360.feature_flags import is_flag_enabled

        with get_db().orm_session() as db:
            assert is_flag_enabled(db, "completely_unknown_flag_xyz") is False

    def test_rollout_percentage_zero_disabled(self):
        from docreview360.db_store import get_db
        from docreview360.feature_flags import is_flag_enabled, set_flag

        with get_db().orm_session() as db:
            set_flag(db, "ai_rewrite", enabled=True, rollout_percentage=0)
            # 0% rollout → always disabled
            assert is_flag_enabled(db, "ai_rewrite", user_id="any_user") is False

    def test_delete_flag_reverts_to_default(self):
        from docreview360.db_store import get_db
        from docreview360.feature_flags import delete_flag, is_flag_enabled, set_flag

        with get_db().orm_session() as db:
            set_flag(db, "beta_editor", enabled=True)
            assert is_flag_enabled(db, "beta_editor") is True
            delete_flag(db, "beta_editor")
            # Back to built-in default (False)
            assert is_flag_enabled(db, "beta_editor") is False

    def test_list_flags_includes_built_ins(self):
        from docreview360.db_store import get_db
        from docreview360.feature_flags import list_flags

        with get_db().orm_session() as db:
            flags = list_flags(db)
            names = [f["flag_name"] for f in flags]
            assert "document_branches" in names
            assert "beta_editor" in names


# ---------------------------------------------------------------------------
# Custom workflow tests
# ---------------------------------------------------------------------------


class TestCustomWorkflows:
    VALID_STEPS = [
        {"step_name": "Technical Review", "role_required": "reviewer", "sla_days": 5},
        {"step_name": "Legal Approval", "role_required": "legal", "sla_days": 10},
    ]

    def test_create_and_list(self):
        from docreview360.custom_workflows import create_custom_workflow, list_custom_workflows
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            wf = create_custom_workflow(
                db,
                org_id="org-wf-1",
                name="Regulatory Review",
                steps=self.VALID_STEPS,
                created_by="admin",
            )
            assert wf.name == "Regulatory Review"
            wfs = list_custom_workflows(db, "org-wf-1")
            assert any(w.name == "Regulatory Review" for w in wfs)

    def test_validate_steps_missing_step_name(self):
        from docreview360.custom_workflows import validate_workflow_steps

        errors = validate_workflow_steps([{"role_required": "reviewer"}])
        assert any("step_name" in e for e in errors)

    def test_validate_steps_missing_role(self):
        from docreview360.custom_workflows import validate_workflow_steps

        errors = validate_workflow_steps([{"step_name": "Review"}])
        assert any("role_required" in e for e in errors)

    def test_validate_steps_duplicate_name(self):
        from docreview360.custom_workflows import validate_workflow_steps

        errors = validate_workflow_steps([
            {"step_name": "Review", "role_required": "reviewer"},
            {"step_name": "Review", "role_required": "approver"},
        ])
        assert any("duplicate" in e.lower() for e in errors)

    def test_validate_steps_negative_sla(self):
        from docreview360.custom_workflows import validate_workflow_steps

        errors = validate_workflow_steps([
            {"step_name": "Review", "role_required": "reviewer", "sla_days": -1}
        ])
        assert any("sla_days" in e for e in errors)

    def test_delete_workflow(self):
        from docreview360.custom_workflows import (
            create_custom_workflow,
            delete_custom_workflow,
            get_custom_workflow,
        )
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            create_custom_workflow(db, "org-del", "Delete Me", self.VALID_STEPS, created_by="admin")
            deleted = delete_custom_workflow(db, "org-del", "Delete Me")
            assert deleted is True
            assert get_custom_workflow(db, "org-del", "Delete Me") is None


# ---------------------------------------------------------------------------
# Custom fields (EAV) tests
# ---------------------------------------------------------------------------


class TestCustomFields:
    def test_create_text_field_and_get_values(self):
        from docreview360.custom_fields import (
            create_field_definition,
            get_field_values,
            set_field_value,
        )
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            defn = create_field_definition(
                db,
                org_id="org-cf-1",
                entity_type="document",
                field_name="classification",
                field_label="Classification",
                field_type="text",
                created_by="admin",
            )
            set_field_value(db, defn.id, "doc-001", "CUI", updated_by="admin")
            values = get_field_values(db, "doc-001", "org-cf-1", "document")
            assert values["classification"] == "CUI"

    def test_validate_number_field(self):
        from docreview360.custom_fields import create_field_definition, validate_field_value
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            defn = create_field_definition(
                db,
                org_id="org-cf-2",
                entity_type="document",
                field_name="page_count",
                field_label="Page Count",
                field_type="number",
                created_by="admin",
            )
            err = validate_field_value(defn, "not-a-number")
            assert err is not None
            assert "number" in err.lower()

            err_ok = validate_field_value(defn, 42)
            assert err_ok is None

    def test_validate_select_field(self):
        from docreview360.custom_fields import create_field_definition, validate_field_value
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            defn = create_field_definition(
                db,
                org_id="org-cf-3",
                entity_type="project",
                field_name="priority",
                field_label="Priority",
                field_type="select",
                options=["low", "medium", "high"],
                created_by="admin",
            )
            err = validate_field_value(defn, "critical")  # not in options
            assert err is not None

            err_ok = validate_field_value(defn, "high")
            assert err_ok is None

    def test_required_field_validation(self):
        from docreview360.custom_fields import create_field_definition, validate_field_value
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            defn = create_field_definition(
                db,
                org_id="org-cf-4",
                entity_type="document",
                field_name="owner",
                field_label="Owner",
                field_type="text",
                required=True,
                created_by="admin",
            )
            err = validate_field_value(defn, None)
            assert err is not None
            assert "required" in err.lower()

    def test_soft_delete_field(self):
        from docreview360.custom_fields import (
            create_field_definition,
            delete_field_definition,
            list_field_definitions,
        )
        from docreview360.db_store import get_db

        with get_db().orm_session() as db:
            defn = create_field_definition(
                db,
                org_id="org-cf-5",
                entity_type="document",
                field_name="archive_reason",
                field_label="Archive Reason",
                field_type="text",
                created_by="admin",
            )
            deleted = delete_field_definition(db, "org-cf-5", defn.id)
            assert deleted is True
            # Should not appear in active list
            active = list_field_definitions(db, "org-cf-5", entity_type="document")
            assert all(d.field_name != "archive_reason" for d in active)
