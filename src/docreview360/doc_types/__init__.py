# SPDX-License-Identifier: MIT
"""Document type management package — backward-compatible re-exports."""

from __future__ import annotations

from ._models import (
    DocumentTypeModel,
    _validate_workflow,
    _WorkflowPayload,
)
from ._registry import (
    DATA_FILE,
    DEFAULT_DOC_TYPE_NAMES,
    DEFAULT_DOC_TYPE_PHASES,
    _bootstrap_if_empty,
    _DocumentTypesView,
    _explicit_clear_active,
    _explicit_clear_lock,
    _row_to_model,
    add_document_type,
    delete_document_type,
    document_types,
    export_document_types,
    export_document_types_json,
    get_document_type,
    import_document_types,
    import_document_types_json,
    list_all_phases,
    list_document_types,
    reset_document_types,
    save_state,
    update_document_type,
)

__all__ = [
    # models
    "DocumentTypeModel",
    "_WorkflowPayload",
    "_validate_workflow",
    # registry / CRUD
    "DEFAULT_DOC_TYPE_PHASES",
    "DEFAULT_DOC_TYPE_NAMES",
    "document_types",
    "add_document_type",
    "get_document_type",
    "list_document_types",
    "update_document_type",
    "delete_document_type",
    "export_document_types",
    "import_document_types",
    "export_document_types_json",
    "import_document_types_json",
    "list_all_phases",
    "reset_document_types",
    # backward compat stubs
    "DATA_FILE",
    "save_state",
    # internal helpers re-exported for backward compat
    "_DocumentTypesView",
    "_bootstrap_if_empty",
    "_explicit_clear_active",
    "_explicit_clear_lock",
    "_row_to_model",
]
