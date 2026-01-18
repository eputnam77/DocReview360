"""Workload estimation, benchmarking and trends."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Sequence

from .document_compare import version_similarity
from .ml.features import quality_features
from .quality import quality_assessment

if TYPE_CHECKING:
    from .ml.torch_models import TinyCritic


def estimate_review_effort(text: str) -> float:
    """Return an effort estimate using critic inputs and outputs."""

    payload = quality_features(text)
    legacy = payload["legacy"]["fann"]
    length = legacy["length"]
    assessment = quality_assessment(text)
    flag_penalty = sum(assessment.flags)
    readability = legacy["readability"]
    style = legacy["style"]
    structure = legacy["structure"]
    repeated = legacy["repeated"]
    # Combine structural heuristics with critic feedback so spikes in the
    # ONNX flags amplify the overall effort budget.
    return (
        length * 1.5
        + repeated * 0.7
        + (1 - readability)
        + (1 - style)
        + (1 - structure)
        + flag_penalty
    )


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
        if window <= 0:
            raise ValueError("window must be positive")
        return [
            sum(scores[i : i + window]) / len(scores[i : i + window])
            for i in range(len(scores) - window + 1)
        ]


def detect_anomalous_document(
    text: str, critic: "TinyCritic | None", history: Sequence[float], threshold: float = 0.3
) -> tuple[bool, float]:
    """Return ``(is_anomalous, score)`` for ``text`` given ``history`` scores."""

    if critic is not None:
        score = critic.predict(text)
        if not history:
            return False, score
        avg = sum(history) / len(history)
        return abs(score - avg) > threshold, score

    assessment = quality_assessment(text)
    score = assessment.score
    if any(flag >= threshold for flag in assessment.flags):
        return True, score
    if not history:
        return False, score
    avg = sum(history) / len(history)
    return abs(score - avg) > threshold, score
