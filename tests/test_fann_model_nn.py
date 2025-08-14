from docreview360.fann_model import Weights, predict, train_model


def test_train_model_learns_basic():
    texts = ["ok", "repeat repeat"]
    labels = [0, 1]
    weights = train_model(texts, labels, epochs=100)
    assert isinstance(weights, Weights)
    score_bad = predict("repeat repeat", weights)
    score_good = predict("ok", weights)
    assert 0 <= score_bad <= 1 and 0 <= score_good <= 1
