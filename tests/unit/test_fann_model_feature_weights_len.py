import pytest
from docreview360.fann_model import Weights, predict_weighted


def test_predict_weighted_validates_feature_weights_length():
    weights = Weights(w1=[[0.0]*6 for _ in range(4)], b1=[0.0]*4, w2=[0.0]*4, b2=0.0)
    with pytest.raises(ValueError):
        predict_weighted("text", weights, feature_weights=[1.0, 2.0])
