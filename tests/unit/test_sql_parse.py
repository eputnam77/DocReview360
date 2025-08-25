from pathlib import Path

from docreview360.database import _parse_sql_statements


def test_parse_sql_ignores_comments(tmp_path: Path) -> None:
    sql = """-- leading comment
CREATE TABLE example(id INT);
-- trailing comment
"""
    file = tmp_path / "mig.sql"
    file.write_text(sql)
    assert _parse_sql_statements(file) == ["CREATE TABLE example(id INT)"]


def test_parse_sql_trigger_and_no_semicolon(tmp_path: Path) -> None:
    sql = """
CREATE TRIGGER trig AFTER INSERT ON demo
BEGIN
  SELECT 1;
END;
CREATE TABLE demo(id INT)
"""
    file = tmp_path / "trig.sql"
    file.write_text(sql)
    stmts = _parse_sql_statements(file)
    assert stmts[0].startswith("CREATE TRIGGER trig")
    assert stmts[1] == "CREATE TABLE demo(id INT)"
