from __future__ import annotations

import xml.etree.ElementTree as ET
from base64 import b64decode


def parse_login_gov_response(saml_response: str) -> str:
    """Return the ``NameID`` from a base64 encoded SAML response."""
    if not saml_response or not saml_response.strip():
        raise ValueError("saml_response required")
    try:
        xml_bytes = b64decode(saml_response)
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
        raise ValueError("invalid SAML response") from exc

    ns = {"saml2": "urn:oasis:names:tc:SAML:2.0:assertion"}
    name_id = root.find(".//saml2:Subject/saml2:NameID", ns)
    if name_id is None or not name_id.text:
        raise ValueError("NameID not found")
    return name_id.text
