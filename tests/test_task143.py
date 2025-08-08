import pytest
from docreview360.stubs.task143 import task143


def test_task143_completed(tmp_path) -> None:
    path = tmp_path / "sample.md"
    result = task143(path=path)
    assert result.exists()


def test_template_listing(tmp_path) -> None:
    path = tmp_path / "templates" / "sample.md"
    result = task143(path=path)
    from docreview360.template_manager import list_templates

    names = list_templates(result.parent)
    assert names == ["sample"]


def test_save_template_validation(tmp_path) -> None:
    from docreview360.template_manager import save_template

    with pytest.raises(ValueError):
        save_template("", "text", root=tmp_path)


def test_list_templates_empty(tmp_path) -> None:
    from docreview360.template_manager import list_templates

    assert list_templates(tmp_path) == []
