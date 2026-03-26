# SPDX-License-Identifier: MIT
"""Domain model package — backward-compatible re-exports from focused sub-modules."""

from __future__ import annotations

from ._audit import AuditLog, AuditLogRecord, LogEntry
from ._base import Base, BaseModel
from ._config import (
    CustomFieldDefinition,
    CustomFieldValue,
    CustomWorkflowTemplate,
    EmailTemplateRecord,
    FeatureFlag,
    GoldenTemplateRecord,
    OrgConfig,
    ProjectConfig,
    ReviewAssignment,
    WOPILockRecord,
)
from ._core import DocumentType, Organization, Phase, PhaseWorkflowLink, Template, User
from ._integration import (
    APIKey,
    BuiltinPluginStateRecord,
    OrgToolConfig,
    Plugin,
    ShareLink,
    WebhookSubscriptionRecord,
)
from ._notifications import (
    VALID_NOTIFICATION_CHANNELS,
    DashboardVisibilityRecord,
    UserNotificationPreference,
)
from ._project import Document, DocumentQualityScore, DocumentVersion, Project
from ._records import DocumentBranch, LegalHold, LegalHoldDocument, NaraMetadata
from ._session import OIDCStateRecord, UserSessionRecord
from ._workflow import (
    Approval,
    ApprovalRecord,
    Workflow,
    WorkflowInstanceRecord,
    WorkflowTemplateRecord,
)

__all__ = [
    # _base
    "Base",
    "BaseModel",
    # _core
    "Organization",
    "User",
    "DocumentType",
    "Phase",
    "PhaseWorkflowLink",
    "Template",
    # _project
    "Project",
    "Document",
    "DocumentVersion",
    "DocumentQualityScore",
    # _workflow
    "Workflow",
    "Approval",
    "ApprovalRecord",
    "WorkflowInstanceRecord",
    "WorkflowTemplateRecord",
    # _session
    "UserSessionRecord",
    "OIDCStateRecord",
    # _notifications
    "VALID_NOTIFICATION_CHANNELS",
    "DashboardVisibilityRecord",
    "UserNotificationPreference",
    # _audit
    "AuditLog",
    "LogEntry",
    "AuditLogRecord",
    # _integration
    "WebhookSubscriptionRecord",
    "Plugin",
    "BuiltinPluginStateRecord",
    "OrgToolConfig",
    "APIKey",
    "ShareLink",
    # _records
    "DocumentBranch",
    "NaraMetadata",
    "LegalHold",
    "LegalHoldDocument",
    # _config
    "EmailTemplateRecord",
    "GoldenTemplateRecord",
    "OrgConfig",
    "ProjectConfig",
    "FeatureFlag",
    "CustomWorkflowTemplate",
    "CustomFieldDefinition",
    "CustomFieldValue",
    "ReviewAssignment",
    "WOPILockRecord",
]
