# SPDX-License-Identifier: MIT
"""Workflow tracking package — backward-compatible re-exports."""

from __future__ import annotations

from ._engine import (
    _bootstrap_sample,
    _persist_workflow,
    advance_workflow,
    assign_reviewer,
    bot_callbacks,
    create_workflow,
    get_approval_steps_for_phase,
    get_workflow,
    list_roles,
    list_workflows,
    load_workflows_from_db,
    register_bot,
    register_callback_url,
    start_workflow,
    workflows,
)
from ._models import (
    ApprovalStep,
    WorkflowModel,
    WorkflowTemplateModel,
    WorkflowTemplatePayload,
    WorkflowTemplateStep,
)
from ._templates import (
    DEFAULT_WORKFLOW_TEMPLATES,
    DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE,
    _coerce_template_payload,
    _ensure_templates_loaded,
    _env_flag_enabled,
    _log_template_issue,
    _raise_template_error,
    _sync_workflow_templates_from_definitions,
    _template_steps_from_definition,
    _validate_template_orders,
    create_workflow_template,
    delete_workflow_template,
    get_workflow_template,
    list_workflow_templates,
    reset_workflow_templates,
    update_workflow_template,
    workflow_template_definitions,
    workflow_templates,
)

__all__ = [
    # models
    "ApprovalStep",
    "WorkflowModel",
    "WorkflowTemplateModel",
    "WorkflowTemplatePayload",
    "WorkflowTemplateStep",
    # engine
    "workflows",
    "bot_callbacks",
    "create_workflow",
    "get_workflow",
    "list_workflows",
    "advance_workflow",
    "start_workflow",
    "assign_reviewer",
    "register_bot",
    "register_callback_url",
    "get_approval_steps_for_phase",
    "list_roles",
    "load_workflows_from_db",
    # templates
    "DEFAULT_WORKFLOW_TEMPLATES",
    "DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE",
    "workflow_templates",
    "workflow_template_definitions",
    "list_workflow_templates",
    "get_workflow_template",
    "create_workflow_template",
    "update_workflow_template",
    "delete_workflow_template",
    "reset_workflow_templates",
    # private helpers re-exported for backward compat
    "_bootstrap_sample",
    "_persist_workflow",
    "_coerce_template_payload",
    "_ensure_templates_loaded",
    "_env_flag_enabled",
    "_log_template_issue",
    "_raise_template_error",
    "_sync_workflow_templates_from_definitions",
    "_template_steps_from_definition",
    "_validate_template_orders",
]
