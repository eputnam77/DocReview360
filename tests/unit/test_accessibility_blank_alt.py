from services.document_checker import run_checks

def test_blank_alt_text_flagged(tmp_path):
    html = "<img alt='  '>"
    path = tmp_path / 'doc.html'
    path.write_text(html, encoding='utf-8')
    result = run_checks(path)
    assert "image missing alt text" in result["accessibility"]
