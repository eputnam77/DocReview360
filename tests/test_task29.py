import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from docreview360.doc_types import (
    DocumentTypeModel,
    add_document_type,
    delete_document_type,
    document_types,
    export_document_types,
    import_document_types,
    list_document_types,
)


def test_document_type_import_export(tmp_path) -> None:
    doc = DocumentTypeModel(name="policy", template="<h1>Policy</h1>", workflow=["Phase"])
    add_document_type(doc)
    export_file = tmp_path / "types.json"
    export_document_types(export_file)

    # clear and reload
    document_types.clear()
    import_document_types(export_file)

    names = {d.name for d in list_document_types()}
    assert "policy" in names

    # cleanup
    delete_document_type("policy")


def test_import_invalid_json(tmp_path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json")
    with pytest.raises(ValueError):
        import_document_types(bad_file)


def test_import_missing_file(tmp_path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(RuntimeError):
        import_document_types(missing)


# ---------------------------------------------------------------------------
# Item 29: threading.Lock guard tests
# ---------------------------------------------------------------------------


def test_vector_search_has_lock() -> None:
    """vector_search._vs_lock must exist and be a threading.Lock."""
    from docreview360 import vector_search

    assert isinstance(vector_search._vs_lock, type(threading.Lock()))


def test_vector_search_concurrent_index_is_safe() -> None:
    """Concurrent calls to index_document must not raise or corrupt state."""
    from docreview360 import vector_search

    vector_search.clear()
    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            vector_search.index_document(f"doc-{i}", f"content number {i}")
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker, i) for i in range(32)]
        for f in as_completed(futures):
            f.result()

    assert not errors, errors
    assert vector_search._total_docs == 32
    vector_search.clear()


def test_cache_has_client_lock() -> None:
    """cache._client_lock must exist and be a threading.Lock."""
    from docreview360 import cache

    assert isinstance(cache._client_lock, type(threading.Lock()))


def test_cache_concurrent_get_set() -> None:
    """Concurrent cache_set / cache_get must not raise."""
    from docreview360 import cache

    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            cache.cache_set(f"k{i}", i)
            cache.cache_get(f"k{i}")
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(worker, i) for i in range(32)]
        for f in as_completed(futures):
            f.result()

    assert not errors, errors
    cache.clear_cache()


def test_template_manager_has_lock() -> None:
    """template_manager._TEMPLATE_LOAD_LOCK must exist."""
    from docreview360 import template_manager

    assert isinstance(template_manager._TEMPLATE_LOAD_LOCK, type(threading.Lock()))


def test_email_templates_has_lock() -> None:
    """email_templates._EMAIL_TEMPLATE_LOAD_LOCK must exist."""
    from docreview360 import email_templates

    assert isinstance(email_templates._EMAIL_TEMPLATE_LOAD_LOCK, type(threading.Lock()))


def test_workflows_has_templates_load_lock() -> None:
    """workflows._TEMPLATES_LOAD_LOCK must exist."""
    from docreview360 import workflows

    assert isinstance(workflows._TEMPLATES_LOAD_LOCK, type(threading.Lock()))
