"""Semantic release helper."""

from ..scripts.semantic_release import run


def task140() -> None:
    """Generate changelog from commits."""
    run()
