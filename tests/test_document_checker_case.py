from services.document_checker import run_checks


def test_repeated_word_detection_case_insensitive(tmp_path):
    path = tmp_path / "doc.txt"
    path.write_text("Hello hello world", encoding="utf-8")

    result = run_checks(path)
    assert "repeated word 'Hello'" in result["grammar"]

