import asyncio
import importlib
import os
import sys
from pathlib import Path

import pytest

# Ensure the source package is importable before referencing it.  Previously the
# ``sys.path`` manipulation occurred *after* importing from ``docreview360``,
# causing ``ModuleNotFoundError`` during test collection on systems where the
# package wasn't installed.  By inserting the repository paths up front we make
# the package available for import in a clean, deterministic way.
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR))

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
    """Ensure global document type registry is reset between tests.

    Tests frequently mutate the ``document_types`` mapping which otherwise
    persists across modules due to being backed by a JSON file.  This fixture
    rebuilds the default document types before each test so that individual
    tests don't interfere with each other.
    """

    document_types.clear()
    for name, phases in DEFAULT_DOC_TYPE_PHASES.items():
        document_types[name] = DocumentTypeModel(
            name=name, template=f"<h1>{name}</h1>", workflow=phases
        )


@pytest.fixture(autouse=True)
def _reset_search(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide an isolated persistent store for the search module per test."""

    db_dir = tmp_path_factory.mktemp("search-db")
    db_path = db_dir / "state.db"
    monkeypatch.setenv("DOCREVIEW360_SEARCH_DB", str(db_path))

    import docreview360.search as search_module

    search_module._reset_state_for_testing(db_path=db_path)
