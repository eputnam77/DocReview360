from __future__ import annotations

import binascii
from base64 import b64decode

from defusedxml import ElementTree as DET
from defusedxml.common import DefusedXmlException

_MAX_SAML_BYTES = 256 * 1024
_UNSAFE_XML_MARKERS = (b"<!DOCTYPE", b"<!ENTITY")


def parse_login_gov_response(saml_response: str) -> str:
    """Return the ``NameID`` from a base64 encoded SAML response."""
    if not isinstance(saml_response, str):
        raise TypeError("saml_response must be a string")
    if not saml_response.strip():
        raise ValueError("saml_response required")
    try:
        compact = "".join(saml_response.split())
        xml_bytes = b64decode(compact, validate=True)
        if len(xml_bytes) > _MAX_SAML_BYTES:
            raise ValueError("SAML response too large")
        normalized = xml_bytes.upper()
        if any(marker in normalized for marker in _UNSAFE_XML_MARKERS):
            raise ValueError("Unsafe XML content")
        root = DET.fromstring(xml_bytes)
    except (binascii.Error, DET.ParseError, DefusedXmlException, ValueError) as exc:
        raise ValueError("invalid SAML response") from exc

    ns = {"saml2": "urn:oasis:names:tc:SAML:2.0:assertion"}
    name_id = root.find(".//saml2:Subject/saml2:NameID", ns)
    if name_id is None or not (name_id.text and name_id.text.strip()):
        raise ValueError("NameID not found")
    return name_id.text.strip()
