"""Reviewer preference learning, consistency tracking and routing."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from .ai_utils import FANN_FEATURE_NAMES, _fann_features


def _feature_dict(text: str) -> Dict[str, float]:
    values = _fann_features(text)
    return dict(zip(FANN_FEATURE_NAMES, values))


@dataclass
class ReviewerProfile:
    preferences: Dict[str, float] = field(
        default_factory=lambda: defaultdict(float)
    )
    decisions: List[bool] = field(default_factory=list)


class ReviewerModel:
    """Minimal model capturing reviewer behaviour."""

    def __init__(self) -> None:
        self._profiles: Dict[str, ReviewerProfile] = {}

    def update_preferences(self, reviewer: str, text: str) -> None:
        feats = _feature_dict(text)
        prof = self._profiles.setdefault(reviewer, ReviewerProfile())
        for name, val in feats.items():
            prof.preferences[name] += val

    def record_decision(self, reviewer: str, approved: bool) -> None:
        prof = self._profiles.setdefault(reviewer, ReviewerProfile())
        prof.decisions.append(approved)

    def consistency_score(self, reviewer: str) -> float:
        prof = self._profiles.get(reviewer)
        if not prof or len(prof.decisions) < 2:
            return 1.0
        same = sum(
            1
            for a, b in zip(prof.decisions, prof.decisions[1:])
            if a == b
        )
        return same / (len(prof.decisions) - 1)

    def route_draft(self, text: str) -> str | None:
        feats = _feature_dict(text)
        best_score = float("-inf")
        best: str | None = None
        for reviewer, prof in self._profiles.items():
            score = sum(prof.preferences.get(k, 0.0) * v for k, v in feats.items())
            if score > best_score:
                best_score = score
                best = reviewer
        return best
