import asyncio
import importlib
import os
import sys
import tempfile
from pathlib import Path
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

doc_types = importlib.import_module("docreview360.doc_types")
DEFAULT_DOC_TYPE_PHASES = doc_types.DEFAULT_DOC_TYPE_PHASES
DocumentTypeModel = doc_types.DocumentTypeModel
document_types = doc_types.document_types

os.environ.setdefault("DOCREVIEW360_SECRET_KEY", "test-secret")
os.environ.setdefault("DOCREVIEW360_ALGORITHM", "HS256")
os.environ.setdefault("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "30")
os.environ.setdefault("DOCREVIEW360_OIDC_SECRET_KEY", "test-oidc")
os.environ.setdefault("DOCREVIEW360_OIDC_ALGORITHM", "HS256")
os.environ.setdefault("DOCREVIEW360_OIDC_EXPIRE_MINUTES", "30")
os.environ.setdefault("DOCREVIEW360_REQUIRE_MFA", "0")
os.environ.setdefault("DOCREVIEW360_MAX_FAILED_ATTEMPTS", "5")
os.environ.setdefault("DOCREVIEW360_LOCKOUT_SECONDS", "300")
os.environ.setdefault("DOCREVIEW360_USER_DB", str(Path("tests") / "docreview360_users.db"))
os.environ.setdefault("DOCREVIEW360_TOKEN_ISSUER", "test-issuer")
os.environ.setdefault("DOCREVIEW360_TOKEN_AUDIENCE", "test-audience")
os.environ.setdefault("DOCREVIEW360_OIDC_TOKEN_ISSUER", "test-oidc-issuer")
os.environ.setdefault("DOCREVIEW360_OIDC_TOKEN_AUDIENCE", "test-oidc-audience")
os.environ.setdefault("DOCREVIEW360_SEED_DEMO_USERS", "0")


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required auth environment variables are set for tests."""

    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DOCREVIEW360_ALGORITHM", "HS256")
    monkeypatch.setenv("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "30")
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
def _reset_document_types() -> None:
    """Ensure the document type registry is reset between tests.

    The registry is now database-backed (Tier 2c).  We reset the shared DB to
    an isolated in-memory instance and re-seed the 27 default document types
    so each test starts from a clean, deterministic state.
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
def _reset_search(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
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
