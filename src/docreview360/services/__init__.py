# SPDX-License-Identifier: MIT
"""Service layer for DocReview360 core business logic (R-14).

Routers should call these services instead of reaching into domain modules
directly.  The service layer is the right place to enforce cross-cutting
concerns such as audit logging, cache invalidation, and permission checks
that are not specific to a single HTTP endpoint.
"""

from .approval_service import ApprovalService
from .document_service import DocumentService
from .project_service import ProjectService

__all__ = [
    "ApprovalService",
    "DocumentService",
    "ProjectService",
]
