import pytest
from docreview360.login_gov import parse_login_gov_response


def test_parse_login_gov_response_type_validation():
    with pytest.raises(TypeError, match="saml_response must be a string"):
        parse_login_gov_response(12345)
