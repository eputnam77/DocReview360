from docreview360.ai_utils import add_feedback_template, generate_feedback


def test_feedback_template_application() -> None:
    add_feedback_template("greet", "Hello {text}!")
    result = generate_feedback("greet", "World")
    assert result == "Hello World!"
