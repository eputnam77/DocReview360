from docreview360 import rbac
import pytest


def test_has_permission_case_insensitive() -> None:
    rbac.set_user_roles("carol", ["Admin"])
    assert rbac.has_permission("carol", "Create")


def test_role_management_and_requirements() -> None:
    rbac.set_user_roles("dave", ["Admin"])
    rbac.add_role("dave", "Reviewer")
    assert rbac.get_roles("dave") == {"admin", "reviewer"}
    assert rbac.has_role("dave", "reviewer")
    user = rbac.auth.User(username="dave", active=True)
    assert rbac.require_role("admin")(user) == user
    with pytest.raises(rbac.HTTPException):
        rbac.require_role("observer")(user)
    assert rbac.require_permission("create")(user) == user
    with pytest.raises(rbac.HTTPException):
        rbac.require_permission("delete")(rbac.auth.User(username="bob", active=True))
