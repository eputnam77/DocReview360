from docreview360.doc_types import DocumentTypeModel
from docreview360.stubs.task214 import task214


def test_task214_sets_default_template() -> None:
    dt = DocumentTypeModel(name="AC", template="t")
    result = task214(dt, "tmpl-1")
    assert result.default_template_id == "tmpl-1"
