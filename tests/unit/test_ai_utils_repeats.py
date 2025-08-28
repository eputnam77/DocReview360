from docreview360.ai_utils import fann_feature_dict


def test_fann_features_detect_punctuated_repeats() -> None:
    feats = fann_feature_dict("hello, hello world")
    assert feats["repeated"] > 0
