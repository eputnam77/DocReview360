import pytest

from docreview360.security_compliance import generate_compliance_pdf


def test_generate_compliance_pdf() -> None:
    pdf = generate_compliance_pdf("flow")
    assert pdf.startswith(b"%PDF-1.4")
    # The PDF should terminate with an EOF marker so that viewers can parse it.
    assert pdf.endswith(b"\n%%EOF\n")


def test_generate_compliance_pdf_validation() -> None:
    with pytest.raises(ValueError):
        generate_compliance_pdf("")
