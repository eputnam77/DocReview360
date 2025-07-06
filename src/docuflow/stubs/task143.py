"""Implementation for task 143."""

from pathlib import Path

from ..template_manager import save_template


def task143(path: Path | None = None) -> Path:
    """Create an example template."""

    target = path or Path("templates/golden") / "sample.md"
    tmpl = save_template("sample", "# Sample", root=target.parent)
    return tmpl
