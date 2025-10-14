from pathlib import Path

from docreview360.ai_utils import FANN_FEATURE_NAMES, _fann_features
from docreview360.ml.torch_models import load_critic, save_critic, train_critic, build_clarity_critic


def test_train_and_predict(tmp_path: Path) -> None:
    critic = build_clarity_critic()
    train_critic(critic, ["ok", "bad bad"], [0, 1], epochs=100, lr=0.05)
    path = save_critic(critic, tmp_path / "model.pt")
    loaded = load_critic(path)
    score_bad = loaded.predict("bad bad")
    score_ok = loaded.predict("ok")
    assert 0 <= score_bad <= 1 and 0 <= score_ok <= 1


def test_readability_feature() -> None:
    idx = FANN_FEATURE_NAMES.index("readability")
    simple = _fann_features("short sentence.")[idx]
    complex_text = (
        "Complexity arises when sentences contain multiple clauses, resulting in longer "
        "constructions and convoluted meaning."
    )
    complex = _fann_features(complex_text)[idx]
    assert simple > complex
