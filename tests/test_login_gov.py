from base64 import b64encode

from docreview360.login_gov import parse_login_gov_response


def test_parse_login_gov_response() -> None:
    saml = (
        "<saml2:Response xmlns:saml2='urn:oasis:names:tc:SAML:2.0:assertion'>"
        "<saml2:Assertion><saml2:Subject>"
        "<saml2:NameID>user@example.com</saml2:NameID>"
        "</saml2:Subject></saml2:Assertion></saml2:Response>"
    )
    encoded = b64encode(saml.encode()).decode()
    assert parse_login_gov_response(encoded) == "user@example.com"
