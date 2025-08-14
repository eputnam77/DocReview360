"""Workload estimation, benchmarking and trends."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Sequence

from .ai_utils import _fann_features
from .document_compare import version_similarity
from .quality import approval_likelihood


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


def benchmark_document(text: str, gold_texts: Sequence[str]) -> float:
    """Return average similarity of ``text`` against ``gold_texts``."""

    if not gold_texts:
        return 0.0
    scores = [version_similarity(text, g) for g in gold_texts]
    return sum(scores) / len(scores)


class ReviewTrends:
    """Track approval likelihood scores over time for trend analysis."""

    def __init__(self) -> None:
        self._scores: Dict[str, List[float]] = defaultdict(list)

    def add(self, project: str, score: float) -> None:
        self._scores[project].append(score)

    def trend(self, project: str) -> List[float]:
        return self._scores.get(project, [])

    def moving_average(self, project: str, window: int = 3) -> List[float]:
        scores = self.trend(project)
        if not scores:
            return []
        return [
            sum(scores[i : i + window]) / len(scores[i : i + window])
            for i in range(len(scores) - window + 1)
        ]


def detect_anomalous_document(
    text: str, weights, history: Sequence[float], threshold: float = 0.3
) -> tuple[bool, float]:
    """Return ``(is_anomalous, score)`` for ``text`` given ``history`` scores."""

    score = approval_likelihood(text, weights)
    if not history:
        return False, score
    avg = sum(history) / len(history)
    return abs(score - avg) > threshold, score
