from pathlib import Path

import pytest

from docreview360 import auth, demo_data, rbac
from docreview360.search import _reset_state_for_testing, get_project, list_projects


def _configure_demo_seed_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user_db = tmp_path / "demo_users.db"
    role_db = tmp_path / "demo_roles.db"
    search_db = tmp_path / "demo_search.db"

    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
    monkeypatch.setenv("DOCREVIEW360_USER_DB", str(user_db))
    monkeypatch.setenv("DOCREVIEW360_RBAC_DB", str(role_db))
    monkeypatch.setenv("DOCREVIEW360_SEARCH_DB", str(search_db))
    monkeypatch.setattr(auth, "SEED_DEMO_USERS", True)

    auth.configure_user_repository(user_db)
    rbac.configure_role_repository(role_db)
    _reset_state_for_testing(db_path=search_db)


def test_seed_demo_data_on_fresh_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_demo_seed_environment(tmp_path, monkeypatch)

    demo_data.seed_demo_data()

    assert auth._get_user_repository().get_user("alice") is not None
    assert auth._get_user_repository().get_user("bob") is not None
    assert get_project("demo-alice") is not None
    assert get_project("demo-bob") is not None


def test_seed_demo_data_on_existing_store_after_upgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_demo_seed_environment(tmp_path, monkeypatch)

    # First seed: fresh store.
    demo_data.seed_demo_data()

    # Second seed: existing store (represents post-upgrade startup reseeding).
    demo_data.seed_demo_data()

    project_ids = [project.id for project in list_projects()]
    assert project_ids.count("demo-alice") == 1
    assert project_ids.count("demo-bob") == 1
