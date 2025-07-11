import pytest

from docreview360.security_compliance import generate_compliance_pdf


def test_generate_compliance_pdf() -> None:
    pdf = generate_compliance_pdf("flow")
    assert pdf.startswith(b"%PDF-1.4")


def test_generate_compliance_pdf_validation() -> None:
    with pytest.raises(ValueError):
        generate_compliance_pdf("")
