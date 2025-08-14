"""Workload estimation and lessons-learned capture."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .ai_utils import _fann_features


def estimate_review_effort(text: str) -> float:
    """Return a simple effort estimate based on FANN features."""
    length, unique, repeated, readability, style, structure = _fann_features(text)
    return length * 2 + repeated * 0.5 + (1 - readability) + (1 - style) + (1 - structure)


class LessonsRepository:
    """Store and aggregate lessons learned across projects."""

    def __init__(self) -> None:
        self._repo: Dict[str, List[str]] = defaultdict(list)

    def add(self, project: str, lesson: str) -> None:
        self._repo[project].append(lesson)

    def aggregate(self) -> Dict[str, List[str]]:
        return dict(self._repo)
