from pathlib import Path

from docreview360.ai_utils import _fann_features
from docreview360.fann_model import load_weights, predict, save_weights, train_model


def test_train_and_predict(tmp_path: Path) -> None:
    weights = train_model(["ok", "bad bad"], [0, 1], epochs=5)
    path = save_weights(weights, tmp_path / "model.json")
    loaded = load_weights(path)
    score_bad = predict("bad bad", loaded)
    score_ok = predict("ok", loaded)
    assert score_bad > score_ok


def test_readability_feature() -> None:
    simple = _fann_features("short sentence.")[-1]
    complex_text = (
        "Complexity arises when sentences contain multiple clauses, resulting in longer "
        "constructions and convoluted meaning."
    )
    complex = _fann_features(complex_text)[-1]
    assert simple > complex
