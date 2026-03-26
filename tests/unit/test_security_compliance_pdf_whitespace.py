import pytest
from docreview360.security_compliance import generate_compliance_pdf


def test_generate_compliance_pdf_whitespace():
    with pytest.raises(ValueError):
        generate_compliance_pdf("   ")
