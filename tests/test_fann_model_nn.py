from docreview360.ml.torch_models import build_clarity_critic, train_critic


def test_train_model_learns_basic():
    texts = ["ok", "repeat repeat"]
    labels = [0, 1]
    critic = build_clarity_critic()
    train_critic(critic, texts, labels, epochs=200, lr=0.05)
    score_bad = critic.predict("repeat repeat")
    score_good = critic.predict("ok")
    assert 0 <= score_bad <= 1 and 0 <= score_good <= 1
    assert score_bad > score_good
