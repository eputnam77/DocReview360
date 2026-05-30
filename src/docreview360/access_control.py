# SPDX-License-Identifier: MIT
"""Shared object-level access checks for API and websocket entrypoints."""

from __future__ import annotations

from fastapi import HTTPException, status
from jose import JWTError, jwt

from . import auth
from .documents import DocumentModel, get_document
from .rbac import has_permission, has_role
from .search import ProjectModel, get_project, list_projects


def is_admin_user(user: auth.User) -> bool:
    """Return True when ``user`` has the admin role."""

    return has_role(user.username, "admin")


def authenticate_bearer_token(raw_token: str) -> auth.User:
    """Validate a raw JWT bearer token without a FastAPI ``Request`` object."""

    decode_kwargs = {
        "algorithms": [auth.ALGORITHM],
        "audience": auth.TOKEN_AUDIENCE,
        "issuer": auth.TOKEN_ISSUER,
    }
    try:
        try:
            payload = jwt.decode(raw_token, auth.SECRET_KEY, **decode_kwargs)
        except JWTError:
            if auth.SECRET_KEY_PREVIOUS is None:
                raise
            payload = jwt.decode(raw_token, auth.SECRET_KEY_PREVIOUS, **decode_kwargs)
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise JWTError("missing subject")
        jti = payload.get("jti")
        if isinstance(jti, str) and jti and auth.is_token_revoked(jti):
            raise JWTError("revoked token")
        token_generation = int(payload.get("gen", 0))
    except (JWTError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    repo = auth._get_user_repository()
    record = repo.get_user(username)
    if record is None:
        demo_defaults = auth.DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and auth._allow_demo_seed():
            repo._seed_user(
                username,
                demo_defaults["password"],
                otp_secret=demo_defaults.get("otp_secret"),
                active=True,
            )
            record = repo.get_user(username)
    if not record or not record.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    if token_generation < record.token_generation:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalidated - please log in again",
        )
    policy = auth._password_policy()
    if policy.max_age_days > 0 and repo.is_password_expired(username, policy.max_age_days):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="password_expired")
    return auth.User(username=username, active=True)


def require_user_permission(user: auth.User, permission: str) -> None:
    """Raise HTTP 403 unless ``user`` has ``permission``."""

    if not has_permission(user.username, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def get_user_org_id(username: str) -> int | None:
    """Return the organization ID for ``username``, if one is assigned."""

    try:
        from .organizations import get_user_org

        org = get_user_org(username=username)
        return org.get("id") if org else None
    except Exception:
        return None


def enforce_org_member(org_id: int, user: auth.User) -> None:
    """Ensure ``user`` is an admin or belongs to ``org_id``."""

    if is_admin_user(user):
        return
    if get_user_org_id(user.username) != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def enforce_project_access(project: ProjectModel, user: auth.User) -> None:
    """Ensure ``user`` can read project-scoped information."""

    if is_admin_user(user):
        return
    if project.org_id is not None:
        enforce_org_member(project.org_id, user)
        return
    if project.user == user.username:
        return
    if project.temp_user == user.username:
        return
    if user.username in project.reviewers:
        return
    if any(p.id == project.id for p in list_projects(user.username)):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def enforce_project_manage_access(project: ProjectModel, user: auth.User) -> None:
    """Ensure ``user`` can mutate project-scoped state."""

    if is_admin_user(user):
        return
    if project.org_id is not None:
        enforce_org_member(project.org_id, user)
    if project.user == user.username:
        return
    if project.temp_user == user.username:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def enforce_project_id_access(project_id: str, user: auth.User) -> ProjectModel:
    """Load and authorize a project by ID."""

    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    enforce_project_access(project, user)
    return project


def enforce_project_id_manage_access(project_id: str, user: auth.User) -> ProjectModel:
    """Load and authorize project mutation by ID."""

    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    enforce_project_manage_access(project, user)
    return project


def enforce_document_access(document: DocumentModel, user: auth.User) -> None:
    """Ensure ``user`` can access a document."""

    if is_admin_user(user):
        return
    if document.user == user.username:
        return
    if document.project:
        project = get_project(document.project)
        if project is not None:
            enforce_project_access(project, user)
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def enforce_document_manage_access(document: DocumentModel, user: auth.User) -> None:
    """Ensure ``user`` can mutate a document or its workflow artifacts."""

    if is_admin_user(user):
        return
    if document.user == user.username:
        return
    if document.project:
        project = get_project(document.project)
        if project is not None:
            enforce_project_manage_access(project, user)
            return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def enforce_document_id_access(doc_id: str, user: auth.User) -> DocumentModel:
    """Load and authorize a document by ID."""

    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    enforce_document_access(document, user)
    return document


def enforce_document_id_manage_access(doc_id: str, user: auth.User) -> DocumentModel:
    """Load and authorize document mutation by ID."""

    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    enforce_document_manage_access(document, user)
    return document


def enforce_document_id_access_if_known(doc_id: str, user: auth.User) -> DocumentModel | None:
    """Authorize ``doc_id`` when present in the document store.

    Some legacy DB-backed routes do not yet mirror every document into the
    in-memory document registry. Admins may operate on those rows; non-admins
    are denied because there is no owner/project metadata to evaluate safely.
    """

    document = get_document(doc_id)
    if document is None:
        if is_admin_user(user):
            return None
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    enforce_document_access(document, user)
    return document


def enforce_document_id_manage_access_if_known(
    doc_id: str,
    user: auth.User,
) -> DocumentModel | None:
    """Authorize mutation of ``doc_id`` when present in the document store."""

    document = get_document(doc_id)
    if document is None:
        if is_admin_user(user):
            return None
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    enforce_document_manage_access(document, user)
    return document
