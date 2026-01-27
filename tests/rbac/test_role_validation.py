import pytest

from docreview360 import rbac


def test_role_mutations_reject_empty_role(tmp_path) -> None:
    rbac.configure_role_repository(tmp_path / "roles.db")
    rbac.reset_role_assignments(include_defaults=False)

    with pytest.raises(ValueError, match="role must be non-empty"):
        rbac.add_role("alice", "   ")

    with pytest.raises(ValueError, match="role must be non-empty"):
        rbac.set_user_roles("alice", ["reviewer", "  "])

    assert rbac.get_roles("alice") == set()
