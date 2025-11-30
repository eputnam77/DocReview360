import pytest

from docreview360.ml.torch_models import build_clarity_critic


def test_predict_weighted_validates_feature_weights_length():
    critic = build_clarity_critic()
    critic.reset_parameters("zeros")
    with pytest.raises(ValueError):
        critic.predict("text", feature_weights=[1.0, 2.0])
