from docuflow.security_compliance import generate_compliance_pdf


def test_generate_compliance_pdf() -> None:
    pdf = generate_compliance_pdf("flow")
    assert pdf.startswith(b"%PDF-1.4")
