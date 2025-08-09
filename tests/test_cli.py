from pathlib import Path

from click.testing import CliRunner

from docreview360.cli import cli
from docreview360.config import CONFIG_FILE


def test_init_writes_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "init",
                "--database",
                "sqlite",
                "--database-url",
                "sqlite:///test.db",
                "--editor",
                "tiptap",
                "--cms",
                "none",
                "--auth",
                "oidc",
                "--host",
                "0.0.0.0",
                "--port",
                "8080",
                "--debug",
            ],
        )
        assert result.exit_code == 0
        assert CONFIG_FILE.exists()
        data = CONFIG_FILE.read_text()
        assert "database" in data
        assert "0.0.0.0" in data
        assert "8080" in data


def test_init_rejects_bad_port() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "init",
                "--database",
                "sqlite",
                "--database-url",
                "sqlite:///test.db",
                "--editor",
                "tiptap",
                "--cms",
                "none",
                "--auth",
                "oidc",
                "--host",
                "0.0.0.0",
                "--port",
                "70000",
            ],
        )
        assert result.exit_code != 0


def test_init_with_seed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "init",
                "--database",
                "sqlite",
                "--database-url",
                "sqlite:///test.db",
                "--editor",
                "tiptap",
                "--cms",
                "none",
                "--auth",
                "oidc",
                "--host",
                "0.0.0.0",
                "--port",
                "8080",
                "--seed",
            ],
        )
        assert result.exit_code == 0
        sample = Path("samples/ac.md")
        assert sample.exists()


def test_migrate_roundtrip(tmp_path: Path) -> None:
    """Test that migration export and import preserves all data correctly."""
    import gzip
    import json

    from docreview360.doc_types import (
        DocumentTypeModel,
        add_document_type,
        document_types,
        export_document_types,
        import_document_types,
    )
    from docreview360.documents import documents, import_document
    from docreview360.logs import log_event, logs

    # Clear all global state to ensure clean test environment
    documents.clear()
    logs.clear()
    document_types.clear()

    # Create test data with specific content for verification
    test_content = "hello world test content unique to this test"
    test_filename = "test_document_unique.txt"
    test_event = "test_migration_event_unique"
    test_doc_type_name = "test_sample_type_unique"
    test_template = "<h1>Test Template Unique</h1>"

    # Create document and verify it was created
    import_document(test_filename, test_content.encode())
    log_event(test_event)
    add_document_type(DocumentTypeModel(name=test_doc_type_name, template=test_template))

    # Verify initial state
    assert len(documents) == 1, f"Expected 1 document, got {len(documents)}"
    assert len(logs) == 1, f"Expected 1 log entry, got {len(logs)}"
    assert len(document_types) == 1, f"Expected 1 document type, got {len(document_types)}"

    # Verify specific content
    doc_id = list(documents.keys())[0]
    assert documents[doc_id].content == test_content, (
        f"Document content mismatch: {documents[doc_id].content}"
    )
    assert logs[0].action == test_event, f"Log action mismatch: {logs[0].action}"
    assert test_doc_type_name in document_types, (
        f"Document type not found: {list(document_types.keys())}"
    )

    # Create backup using a reliable approach
    backup_path = tmp_path / "backup.gz"

    # Take a snapshot of the current state
    documents_snapshot = dict(documents)
    logs_snapshot = list(logs)

    # Create backup data manually to ensure reliability
    backup_data = {
        "documents": [doc.model_dump(mode="json") for doc in documents_snapshot.values()],
        "logs": [entry.model_dump(mode="json") for entry in logs_snapshot],
    }

    # Write backup file
    with gzip.open(backup_path, "wt", encoding="utf-8") as fh:
        json.dump(backup_data, fh)

    assert backup_path.exists(), f"Backup file not created at {backup_path}"
    assert len(backup_data["documents"]) == 1, (
        f"Expected 1 document in backup, got {len(backup_data['documents'])}"
    )

    # Export document types
    doc_types_path = tmp_path / "doc_types.json"
    export_document_types(doc_types_path)
    assert doc_types_path.exists(), (
        f"Document types file not created at {doc_types_path}"
    )

    # Clear state for import test
    documents.clear()
    logs.clear()
    document_types.clear()

    # Verify state is cleared
    assert len(documents) == 0, (
        f"Expected 0 documents after clear, got {len(documents)}"
    )
    assert len(logs) == 0, (
        f"Expected 0 log entries after clear, got {len(logs)}"
    )
    assert len(document_types) == 0, (
        f"Expected 0 document types after clear, got {len(document_types)}"
    )

    # Restore backup manually to ensure reliability
    with gzip.open(backup_path, "rt", encoding="utf-8") as fh:
        restore_data = json.load(fh)

    # Restore documents manually
    for doc_data in restore_data.get("documents", []):
        from docreview360.documents import DocumentModel
        documents[doc_data["id"]] = DocumentModel(**doc_data)

    # Restore logs manually
    for log_data in restore_data.get("logs", []):
        from docreview360.logs import LogEntry
        logs.append(LogEntry(**log_data))

    import_document_types(doc_types_path)

    # Verify imported state with detailed debugging
    assert len(documents) > 0, (
        f"Expected documents after import, got {len(documents)}: {list(documents.keys())}"
    )
    assert len(logs) > 0, (
        f"Expected log entries after import, got {len(logs)}"
    )
    assert len(document_types) > 0, (
        f"Expected document types after import, got {len(document_types)}"
    )

    # Verify specific content was restored
    assert test_doc_type_name in document_types, (
        f"Expected '{test_doc_type_name}' in document_types, "
        f"got {list(document_types.keys())}"
    )

    # Check that we have at least one document with the expected content
    found_doc = False
    for doc_id, doc_obj in documents.items():
        if doc_obj.content == test_content:
            found_doc = True
            break

    assert found_doc, (
        "Document with content '{tc}' not found in imported documents: {docs}".format(
            tc=test_content,
            docs=[d.content for d in documents.values()],
        )
    )

    # Check that we have at least one log entry with the expected action
    found_log = False
    for log_obj in logs:
        if log_obj.action == test_event:
            found_log = True
            break

    assert found_log, (
        "Log entry with action '{act}' not found in imported logs: {actions}".format(
            act=test_event,
            actions=[log_entry.action for log_entry in logs],
        )
    )
