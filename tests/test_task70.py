import docuflow.ai_utils as ai


def test_synthlang_reduces_tokens() -> None:
    ai.synth_enabled = True
    text = "Documentation"
    compressed = ai.synth_compress(text)
    assert len(compressed) < len(text)
    ai.synth_enabled = False
