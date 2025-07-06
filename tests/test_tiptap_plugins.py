from docuflow.tiptap import markdown_to_tiptap
from docuflow.tiptap_plugins import lint_template_plugin, numbering_plugin


def test_lint_template_plugin() -> None:
    data = markdown_to_tiptap("# Intro\ntext")
    rules = {"required_headings": ["Intro", "Methods"]}
    issues = lint_template_plugin(data, rules)
    assert "missing heading 'Methods'" in issues


def test_numbering_plugin() -> None:
    data = markdown_to_tiptap("# Intro")
    result = numbering_plugin(data, {"Intro": "1"})
    assert result["content"][0]["content"][0]["text"] == "# 1 Intro"
