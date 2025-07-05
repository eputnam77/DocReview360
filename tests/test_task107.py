from pathlib import Path

from docuflow.fann_model import load_weights, predict, save_weights, train_model


def test_train_and_predict(tmp_path: Path) -> None:
    weights = train_model(["ok", "bad bad"], [0, 1], epochs=5)
    path = save_weights(weights, tmp_path / "model.json")
    loaded = load_weights(path)
    score_bad = predict("bad bad", loaded)
    score_ok = predict("ok", loaded)
    assert score_bad > score_ok
