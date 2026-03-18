"""Pytest configuration and shared fixtures.

## Test Isolation Model (addresses RELEASE_CHECKLIST.md Item 8c)

Each test runs against a fresh in-memory SQLite database:

1. ``_reset_document_types`` (autouse) calls ``reset_db("sqlite+pysqlite:///:memory:")``
   before every test, creating a brand-new engine + StaticPool connection.
   ``reset_document_types(seed=True)`` and ``reset_phases()`` re-populate the
   DB-backed registries.  After the test, ``reset_db(None)`` releases the engine.

2. The ``testing_db`` fixture (opt-in) provides explicit access to the per-test
   :class:`~docreview360.database.Database` instance so tests that need to execute
   raw SQL or verify DB state can do so without bypassing the ORM layer.

3. The ``_reset_approvals`` fixture (autouse) clears in-memory approval state
   between tests so the approval dict does not leak across test boundaries.

Known limitation: ~20 tests use ``monkeypatch.setattr`` on module-level
functions (``log_event``, ``_upload_approval_artifacts``, etc.).  Those tests
are safe because monkeypatch reverts all patches after each test.  The two tests
that patch ``phases._phases`` directly
(``tests/unit/test_phases_errors.py``,
``tests/unit/test_phases_whitespace.py``) are also safe for the same reason.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from uuid import uuid4

import pytest

# Ensure the source package is importable before referencing it.  Previously the
# ``sys.path`` manipulation occurred *after* importing from ``docreview360``,
# causing ``ModuleNotFoundError`` during test collection on systems where the
# package wasn't installed.  By inserting the repository paths up front we make
# the package available for import in a clean, deterministic way.
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR))


def _configure_test_tempdir() -> None:
    """Ensure pytest temp directories are writable for this workspace."""

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            probe_file = Path(temp_dir) / "probe.txt"
            probe_file.write_text("ok", encoding="utf-8")
        return
    except Exception:
        fallback = BASE_DIR / ".tmp" / f"pytest-{uuid4().hex}"
        fallback.mkdir(parents=True, exist_ok=True)
        os.environ["TMPDIR"] = str(fallback)
        os.environ["TEMP"] = str(fallback)
        os.environ["TMP"] = str(fallback)
        tempfile.tempdir = str(fallback)


_configure_test_tempdir()

os.environ.setdefault("DOCREVIEW360_SECRET_KEY", "test-secret")
os.environ.setdefault("DOCREVIEW360_ALGORITHM", "HS256")
os.environ.setdefault("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "30")
os.environ.setdefault("DOCREVIEW360_REFRESH_EXPIRE_DAYS", "30")
os.environ.setdefault("DOCREVIEW360_OIDC_SECRET_KEY", "test-oidc")
os.environ.setdefault("DOCREVIEW360_OIDC_ALGORITHM", "HS256")
os.environ.setdefault("DOCREVIEW360_OIDC_EXPIRE_MINUTES", "30")
os.environ.setdefault("DOCREVIEW360_REQUIRE_MFA", "0")
os.environ.setdefault("DOCREVIEW360_MAX_FAILED_ATTEMPTS", "5")
os.environ.setdefault("DOCREVIEW360_LOCKOUT_SECONDS", "300")
os.environ.setdefault("DOCREVIEW360_USER_DB", str(Path("tests") / "docreview360_users.db"))
os.environ.setdefault("DOCREVIEW360_RBAC_DB", str(Path("tests") / "docreview360_roles.db"))
os.environ.setdefault("DOCREVIEW360_TOKEN_ISSUER", "test-issuer")
os.environ.setdefault("DOCREVIEW360_TOKEN_AUDIENCE", "test-audience")
os.environ.setdefault("DOCREVIEW360_OIDC_TOKEN_ISSUER", "test-oidc-issuer")
os.environ.setdefault("DOCREVIEW360_OIDC_TOKEN_AUDIENCE", "test-oidc-audience")
os.environ.setdefault("DOCREVIEW360_SEED_DEMO_USERS", "0")


@pytest.fixture(autouse=True)
def _restore_auth_module() -> Generator[None, None, None]:
    """Restore sys.modules['docreview360.auth'] after tests that pop/reimport it.

    Some tests pop docreview360.auth from sys.modules and reimport it to test
    import-time behaviour (e.g. reading env vars at startup).  This creates a
    *new* module object in sys.modules while other test files still hold a
    reference to the *original* module.  The mismatch breaks
    ``_get_user_repository()`` which looks up the module via sys.modules to
    locate USER_REPOSITORY.  This fixture saves the original module and restores
    it after every test.
    """
    import sys

    original = sys.modules.get("docreview360.auth")
    yield
    try:
        if original is not None and sys.modules.get("docreview360.auth") is not original:
            sys.modules["docreview360.auth"] = original
            # Also patch back into the package namespace if needed
            try:
                import docreview360 as _pkg
                if getattr(_pkg, "auth", None) is not original:
                    _pkg.auth = original
            except Exception:
                pass
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required auth environment variables are set for tests."""

    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DOCREVIEW360_ALGORITHM", "HS256")
    monkeypatch.setenv("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("DOCREVIEW360_REFRESH_EXPIRE_DAYS", "30")
    monkeypatch.setenv("DOCREVIEW360_OIDC_SECRET_KEY", "test-oidc")
    monkeypatch.setenv("DOCREVIEW360_OIDC_ALGORITHM", "HS256")
    monkeypatch.setenv("DOCREVIEW360_OIDC_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("DOCREVIEW360_REQUIRE_MFA", "0")
    monkeypatch.setenv("DOCREVIEW360_MAX_FAILED_ATTEMPTS", "5")
    monkeypatch.setenv("DOCREVIEW360_LOCKOUT_SECONDS", "300")
    monkeypatch.setenv("DOCREVIEW360_USER_DB", str(Path("tests") / "docreview360_users.db"))
    monkeypatch.setenv("DOCREVIEW360_TOKEN_ISSUER", "test-issuer")
    monkeypatch.setenv("DOCREVIEW360_TOKEN_AUDIENCE", "test-audience")
    monkeypatch.setenv("DOCREVIEW360_OIDC_TOKEN_ISSUER", "test-oidc-issuer")
    monkeypatch.setenv("DOCREVIEW360_OIDC_TOKEN_AUDIENCE", "test-oidc-audience")
    monkeypatch.setenv("DOCREVIEW360_SEED_DEMO_USERS", "0")
    # Ensure a safe non-production environment for every test so that tests
    # which temporarily set DOCREVIEW360_ENV=production/prod do not pollute
    # subsequent tests via direct os.environ modifications.
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
    # Prevent module-level os.environ.setdefault calls in some test files from
    # leaking DOCREVIEW360_DATABASE_URL into Config.load() env override logic.
    monkeypatch.delenv("DOCREVIEW360_DATABASE_URL", raising=False)
    monkeypatch.delenv("DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP", raising=False)


@pytest.hookimpl
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Execute async test functions without external plugins.

    The kata environment may not include ``pytest-asyncio``. This hook
    provides a very small event loop runner so tests marked as async can
    still execute.  It mirrors the minimal behavior of the real plugin
    by detecting coroutine functions and running them to completion.
    """

    if asyncio.iscoroutinefunction(pyfuncitem.obj):
        loop = asyncio.new_event_loop()
        try:
            kwargs = {name: pyfuncitem.funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
            loop.run_until_complete(pyfuncitem.obj(**kwargs))
        finally:
            loop.close()
        return True
    return None


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used throughout the tests."""

    config.addinivalue_line("markers", "asyncio: run test as async")


@pytest.fixture(autouse=True)
def _reset_document_types() -> Generator[None, None, None]:
    """Ensure the document type registry is reset between tests.

    The registry is now database-backed (Tier 2c).  We reset the shared DB to
    an isolated in-memory instance and re-seed the 27 default document types
    so each test starts from a clean, deterministic state.

    Each test gets its own SQLAlchemy engine backed by a private in-memory
    SQLite database (StaticPool keeps the connection alive for the engine's
    lifetime).  This guarantees no data leaks between tests.
    """

    from docreview360.db_store import reset_db
    from docreview360.doc_types import reset_document_types
    from docreview360.phases import reset_phases

    reset_db("sqlite+pysqlite:///:memory:")
    reset_document_types(seed=True)
    reset_phases()
    yield
    reset_db(None)


@pytest.fixture(autouse=True)
def _reset_role_permissions(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    """Restore ROLE_PERMISSIONS and role assignments between tests.

    Creates a fresh per-test role repository so that tests which call
    ``rbac.reset_role_assignments()`` or ``rbac.configure_role_repository()``
    do not leak role state into subsequent tests.
    """
    try:
        from docreview360 import rbac

        rbac_dir = tmp_path_factory.mktemp("rbac")
        rbac_path = rbac_dir / "roles.db"
        monkeypatch.setenv("DOCREVIEW360_RBAC_DB", str(rbac_path))
        rbac.configure_role_repository(rbac_path)
        rbac.reset_role_assignments()
        rbac._ROLE_CACHE.invalidate()
    except Exception:
        pass
    yield
    try:
        from docreview360 import rbac

        rbac.ROLE_PERMISSIONS.clear()
        rbac.ROLE_PERMISSIONS.update(
            {role: set(perms) for role, perms in rbac._DEFAULT_ROLE_PERMISSIONS.items()}
        )
        rbac._ROLE_PERMISSIONS_LAST_CHECK = 0.0
        rbac._ROLE_PERMISSIONS_MTIME = None
        rbac._ROLE_CACHE.invalidate()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_approvals() -> Generator[None, None, None]:
    """Reset in-memory approval state between tests.

    The approvals module keeps a module-level ``approvals`` dict that is
    DB-backed for production use but still has an in-memory cache layer.
    Clearing it between tests prevents approval state leaking across boundaries.
    """
    try:
        import docreview360.approvals as approvals_mod

        if hasattr(approvals_mod, "approvals") and hasattr(
            approvals_mod.approvals, "clear"
        ):
            approvals_mod.approvals.clear()
    except Exception:
        pass
    yield
    try:
        import docreview360.approvals as approvals_mod

        if hasattr(approvals_mod, "approvals") and hasattr(
            approvals_mod.approvals, "clear"
        ):
            approvals_mod.approvals.clear()
    except Exception:
        pass


@pytest.fixture()
def testing_db():
    """Provide direct access to the per-test Database instance.

    Use this fixture when a test needs to execute raw SQL or verify
    schema state without going through the ORM layer.  The DB is
    automatically reset between tests by ``_reset_document_types``.

    Example::

        def test_something(testing_db) -> None:
            with testing_db.session() as conn:
                rows = conn.execute(text("SELECT * FROM document_types")).fetchall()
            assert len(rows) == 27
    """
    from docreview360.db_store import get_db

    return get_db()


@pytest.fixture(autouse=True)
def _isolate_settings(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    """Redirect settings_manager.SETTINGS_FILE to an isolated per-test path.

    Tests that call settings endpoints write to ``settings.yaml`` in the repo
    root, polluting subsequent test runs.  This fixture points the module-level
    ``SETTINGS_FILE`` at a fresh temp file so those writes don't persist.
    """
    try:
        settings_dir = tmp_path_factory.mktemp("settings")
    except PermissionError:
        fallback_root = BASE_DIR / ".tmp" / "pytest"
        fallback_root.mkdir(parents=True, exist_ok=True)
        settings_dir = fallback_root / f"settings-{uuid4().hex}"
        settings_dir.mkdir(parents=True, exist_ok=True)

    import docreview360.settings_manager as _sm

    monkeypatch.setattr(_sm, "SETTINGS_FILE", settings_dir / "settings.yaml")
    yield


@pytest.fixture(autouse=True)
def _reset_search(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    """Provide an isolated persistent store for the search module per test."""

    try:
        db_dir = tmp_path_factory.mktemp("search-db")
    except PermissionError:
        fallback_root = BASE_DIR / ".tmp" / "pytest"
        fallback_root.mkdir(parents=True, exist_ok=True)
        db_dir = fallback_root / f"search-db-{uuid4().hex}"
        db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "state.db"
    monkeypatch.setenv("DOCREVIEW360_SEARCH_DB", str(db_path))

    import docreview360.search as search_module

    search_module._reset_state_for_testing(db_path=db_path)
    yield
    search_module._repository.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> Generator[None, None, None]:
    """Reset API rate limiter counters between tests to prevent state leakage."""
    try:
        from docreview360.api import reset_rate_limiters_for_testing

        reset_rate_limiters_for_testing()
    except Exception:
        pass
    yield
    try:
        from docreview360.api import reset_rate_limiters_for_testing

        reset_rate_limiters_for_testing()
    except Exception:
        pass
