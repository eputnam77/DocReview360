"""Reviewer preference learning, consistency tracking and routing."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Sequence

import numpy as np

from .ml.features import quality_features
from .ml.onnx_infer import ModelMetadata, get_model_metadata, get_session, infer
from .ml.routing_critic import ROUTING_FEATURE_NAMES, routing_feature_vector
from .ml.torch_models import TinyCritic, update_critic

_DEFAULT_ROUTING_MODEL = Path(__file__).resolve().parent / "ml" / "assets" / "routing_reviewer.onnx"
_FALLBACK_REVIEWERS: tuple[str, ...] = ("alice", "bob", "charlie")
_FALLBACK_APPROVAL_WEIGHTS = np.array([0.6, 0.2, -0.3, 0.4, 0.5, 0.1], dtype=np.float32)
_FALLBACK_APPROVAL_BIAS = -0.1
_FALLBACK_REVIEWER_WEIGHTS = np.array(
    [
        [0.3, 0.1, -0.2, 0.4, 0.2, 0.1],
        [0.2, 0.3, -0.1, 0.1, 0.5, 0.2],
        [0.1, 0.2, -0.3, 0.2, 0.1, 0.4],
    ],
    dtype=np.float32,
)

_LATENCY_BUCKETS: tuple[tuple[float, str], ...] = (
    (0.01, "<10ms"),
    (0.05, "10-50ms"),
    (0.1, "50-100ms"),
)
_LATENCY_DEFAULT = "100ms+"


def _feature_dict(text: str) -> Dict[str, float]:
    payload = quality_features(text)
    return dict(payload["legacy"]["fann"])


@dataclass
class ReviewerProfile:
    preferences: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    decisions: List[bool] = field(default_factory=list)


@dataclass
class Recommendation:
    """Container holding routing recommendations."""

    approval_likelihood: float
    ranked_reviewers: List[tuple[str, float]]
    features: np.ndarray

    @property
    def primary(self) -> str | None:
        if not self.ranked_reviewers:
            return None
        return self.ranked_reviewers[0][0]


class ReviewerModel:
    """Model capturing reviewer behaviour and routing recommendations."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        providers: Sequence[str] | None = None,
    ) -> None:
        self._model_path = Path(model_path) if model_path else _DEFAULT_ROUTING_MODEL
        session: Any | None = None
        metadata: ModelMetadata | None = None
        try:
            session = get_session(self._model_path, providers=providers)
            metadata = get_model_metadata(session)
            reviewers_meta = metadata.custom_metadata.get("docreview360:reviewers", "")
            reviewers = tuple(filter(None, (name.strip() for name in reviewers_meta.split(","))))
        except Exception:
            reviewers = _FALLBACK_REVIEWERS
            metadata = ModelMetadata(
                path=self._model_path,
                sha256=_hash_path(self._model_path),
                version=None,
                custom_metadata={"docreview360:reviewers": ",".join(reviewers)},
            )
        else:
            if not reviewers:
                reviewers = _FALLBACK_REVIEWERS
        self._session = session
        self._metadata = metadata
        self._reviewers: tuple[str, ...] = reviewers
        self._feature_dim = len(ROUTING_FEATURE_NAMES)
        self._profiles: Dict[str, ReviewerProfile] = {}
        self._embedding_stats: Dict[str, dict[str, Any]] = {}
        self._feedback_counts: Dict[str, Dict[str, int]] = {}
        self._latency_buckets: Dict[str, int] = {label: 0 for _, label in _LATENCY_BUCKETS}
        self._latency_buckets[_LATENCY_DEFAULT] = 0
        for reviewer in reviewers:
            self._ensure_stats(reviewer)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        """Serialise routing state to ``path``."""

        data = {
            "profiles": {name: asdict(profile) for name, profile in self._profiles.items()},
            "embeddings": {
                name: {
                    "count": stats["count"],
                    "vector": stats["vector"].tolist(),
                }
                for name, stats in self._embedding_stats.items()
            },
            "feedback": self._feedback_counts,
            "latency": self._latency_buckets,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    def load(self, path: str) -> None:
        """Load routing state from ``path`` created by :meth:`save`."""

        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)

        # Backwards compatibility: legacy payloads stored the profile mapping
        # at the top level rather than under ``profiles``.
        profiles_data = payload.get("profiles")
        if profiles_data is None:
            profiles_data = payload

        self._profiles = {
            name: ReviewerProfile(
                preferences=defaultdict(float, prof.get("preferences", {})),
                decisions=list(prof.get("decisions", [])),
            )
            for name, prof in profiles_data.items()
        }

        embeddings = payload.get("embeddings", {})
        self._embedding_stats = {}
        for name, stats in embeddings.items():
            vector = np.array(stats.get("vector", [0.0] * self._feature_dim), dtype=np.float32)
            self._embedding_stats[name] = {
                "count": int(stats.get("count", 0)),
                "vector": vector,
            }

        feedback = payload.get("feedback", {})
        self._feedback_counts = {
            name: {
                "approved": int(info.get("approved", 0)),
                "rejected": int(info.get("rejected", 0)),
            }
            for name, info in feedback.items()
        }

        latency = payload.get("latency", {})
        self._latency_buckets = {label: int(latency.get(label, 0)) for _, label in _LATENCY_BUCKETS}
        self._latency_buckets[_LATENCY_DEFAULT] = int(latency.get(_LATENCY_DEFAULT, 0))

        for reviewer in self._reviewers:
            self._ensure_stats(reviewer)

    # ------------------------------------------------------------------
    # Reviewer preference tracking
    # ------------------------------------------------------------------
    def _ensure_stats(self, reviewer: str) -> None:
        self._embedding_stats.setdefault(
            reviewer,
            {
                "count": 0,
                "vector": np.zeros(self._feature_dim, dtype=np.float32),
            },
        )
        self._feedback_counts.setdefault(
            reviewer,
            {
                "approved": 0,
                "rejected": 0,
            },
        )

    def update_preferences(self, reviewer: str, text: str) -> None:
        feats = _feature_dict(text)
        prof = self._profiles.setdefault(reviewer, ReviewerProfile())
        for name, val in feats.items():
            prof.preferences[name] += val

    def record_decision(self, reviewer: str, approved: bool) -> None:
        prof = self._profiles.setdefault(reviewer, ReviewerProfile())
        prof.decisions.append(approved)
        stats = self._feedback_counts.setdefault(
            reviewer,
            {"approved": 0, "rejected": 0},
        )
        if approved:
            stats["approved"] += 1
        else:
            stats["rejected"] += 1

    def consistency_score(self, reviewer: str) -> float:
        prof = self._profiles.get(reviewer)
        if not prof or len(prof.decisions) < 2:
            return 1.0
        same = sum(1 for a, b in zip(prof.decisions, prof.decisions[1:]) if a == b)
        return same / (len(prof.decisions) - 1)

        # ------------------------------------------------------------------

    # Routing and inference helpers
    # ------------------------------------------------------------------
    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        shifted = logits - logits.max()
        exp = np.exp(shifted)
        denom = exp.sum()
        if denom == 0:
            return np.full_like(exp, 1.0 / len(exp))
        return exp / denom

    def _bucket_latency(self, elapsed: float) -> str:
        for threshold, label in _LATENCY_BUCKETS:
            if elapsed <= threshold:
                return label
        return _LATENCY_DEFAULT

    def _update_embedding(self, reviewer: str, features: np.ndarray) -> None:
        stats = self._embedding_stats.setdefault(
            reviewer,
            {
                "count": 0,
                "vector": np.zeros(self._feature_dim, dtype=np.float32),
            },
        )
        stats["vector"] += features
        stats["count"] += 1

    def recommend(self, text: str, k: int = 3) -> Recommendation:
        """Return top-``k`` reviewer recommendations for ``text``."""

        features = routing_feature_vector(text)
        start = perf_counter()
        if self._session is not None:
            approval_arr, reviewer_logits = infer(self._session, {"input": features.reshape(1, -1)})
            approval_likelihood = float(np.clip(approval_arr.squeeze().item(), 0.0, 1.0))
            logits = reviewer_logits.squeeze(0)
        else:
            approval_linear = float(
                np.dot(_FALLBACK_APPROVAL_WEIGHTS, features) + _FALLBACK_APPROVAL_BIAS
            )
            approval_likelihood = _sigmoid_scalar(approval_linear)
            logits = _FALLBACK_REVIEWER_WEIGHTS @ features
        elapsed = perf_counter() - start
        bucket = self._bucket_latency(elapsed)
        self._latency_buckets[bucket] += 1

        probabilities = self._softmax(logits)
        order = np.argsort(logits)[::-1]
        ranked: List[tuple[str, float]] = []
        for idx in order[: max(1, k)]:
            reviewer = self._reviewers[idx]
            prob = float(probabilities[idx])
            ranked.append((reviewer, prob))
            self._update_embedding(reviewer, features)
        return Recommendation(approval_likelihood, ranked, features)

    def route_draft(self, text: str) -> str | None:
        recommendation = self.recommend(text, k=1)
        return recommendation.primary

    def ingest_feedback(
        self, reviewer: str, text: str, approved: bool, critic: TinyCritic
    ) -> TinyCritic:
        """Incorporate reviewer feedback and update the global model."""

        self.update_preferences(reviewer, text)
        self.record_decision(reviewer, approved)
        label = 1 if approved else 0
        return update_critic(critic, [text], [label])

    # ------------------------------------------------------------------
    # Analytics helpers
    # ------------------------------------------------------------------
    def approval_rate(self, reviewer: str) -> float:
        prof = self._profiles.get(reviewer)
        if not prof or not prof.decisions:
            return 1.0
        return sum(1 for d in prof.decisions if d) / len(prof.decisions)

    def anomalous_reviewers(self, threshold: float = 0.2) -> List[str]:
        if not self._profiles:
            return []
        rates = {r: self.approval_rate(r) for r, prof in self._profiles.items() if prof.decisions}
        if not rates:
            return []
        avg = sum(rates.values()) / len(rates)
        return [r for r, rate in rates.items() if abs(rate - avg) > threshold]

    @property
    def reviewer_embeddings(self) -> Dict[str, List[float]]:
        embeddings: Dict[str, List[float]] = {}
        for reviewer, stats in self._embedding_stats.items():
            count = stats.get("count", 0)
            vector = stats.get("vector")
            if count:
                embeddings[reviewer] = (vector / count).tolist()
            else:
                embeddings[reviewer] = [0.0] * self._feature_dim
        return embeddings

    @property
    def reviewer_feedback(self) -> Dict[str, Dict[str, int]]:
        return {name: dict(counts) for name, counts in self._feedback_counts.items()}

    @property
    def latency_buckets(self) -> Dict[str, int]:
        return dict(self._latency_buckets)

    @property
    def model_metadata(self) -> "ModelMetadata":
        """Return metadata describing the underlying routing critic."""

        return self._metadata


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
    except FileNotFoundError:
        pass
    return digest.hexdigest()


def _sigmoid_scalar(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)
