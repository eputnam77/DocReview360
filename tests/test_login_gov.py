from base64 import b64encode

import pytest

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


def test_parse_login_gov_response_blank() -> None:
    """Whitespace-only input should raise an explicit error."""
    try:
        parse_login_gov_response("   ")
    except ValueError as exc:
        assert "saml_response" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("ValueError not raised for blank input")


def test_parse_login_gov_response_invalid_base64() -> None:
    """Non-base64 input should raise a clear error."""
    with pytest.raises(ValueError):
        parse_login_gov_response("not base64")


def test_parse_login_gov_response_missing_nameid() -> None:
    """Responses lacking ``NameID`` should be rejected."""
    saml = (
        "<saml2:Response xmlns:saml2='urn:oasis:names:tc:SAML:2.0:assertion'>"
        "<saml2:Assertion><saml2:Subject>"  # no NameID element
        "</saml2:Subject></saml2:Assertion></saml2:Response>"
    )
    encoded = b64encode(saml.encode()).decode()
    with pytest.raises(ValueError):
        parse_login_gov_response(encoded)


def test_parse_login_gov_response_whitespace_nameid() -> None:
    """Whitespace-only NameID values should be treated as missing."""
    saml = (
        "<saml2:Response xmlns:saml2='urn:oasis:names:tc:SAML:2.0:assertion'>"
        "<saml2:Assertion><saml2:Subject>"
        "<saml2:NameID>   </saml2:NameID>"
        "</saml2:Subject></saml2:Assertion></saml2:Response>"
    )
    encoded = b64encode(saml.encode()).decode()
    with pytest.raises(ValueError):
        parse_login_gov_response(encoded)


def test_parse_login_gov_response_rejects_dtd_payload() -> None:
    saml = (
        "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>"
        "<saml2:Response xmlns:saml2='urn:oasis:names:tc:SAML:2.0:assertion'>"
        "<saml2:Assertion><saml2:Subject>"
        "<saml2:NameID>user@example.com</saml2:NameID>"
        "</saml2:Subject></saml2:Assertion></saml2:Response>"
    )
    encoded = b64encode(saml.encode()).decode()
    with pytest.raises(ValueError):
        parse_login_gov_response(encoded)


def test_parse_login_gov_response_rejects_oversized_payload() -> None:
    long_name = "a" * (300 * 1024)
    saml = (
        "<saml2:Response xmlns:saml2='urn:oasis:names:tc:SAML:2.0:assertion'>"
        "<saml2:Assertion><saml2:Subject>"
        f"<saml2:NameID>{long_name}</saml2:NameID>"
        "</saml2:Subject></saml2:Assertion></saml2:Response>"
    )
    encoded = b64encode(saml.encode()).decode()
    with pytest.raises(ValueError):
        parse_login_gov_response(encoded)
