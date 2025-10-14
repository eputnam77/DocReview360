"""Machine learning focused API endpoints."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from threading import Lock
from time import monotonic
from typing import Deque, Mapping

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, conlist

from .. import auth
from ..audit import log_audit_event
from ..logs import log_call
from ..ml.compliance_classifier import evaluate_compliance
from ..ml.features import SIGNATURE_ANOMALY_FEATURE_NAMES
from ..ml.signature_anomaly import (
    get_signature_anomaly_metadata,
    score_signature_anomaly,
)
from ..quality import QUALITY_FLAG_NAMES, high_risk_warnings, quality_assessment
from ..rbac import require_permission
from ..reviewer_model import Recommendation, ReviewerModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["machine-learning"])

_RATE_LIMIT_CALLS = 5
_RATE_LIMIT_WINDOW_SECONDS = 60.0


class RateLimiter:
    """Simple fixed-window rate limiter keyed by an identifier."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._limit = int(limit)
        self._window = float(window_seconds)
        self._hits: dict[str, Deque[float]] = {}
        self._lock = Lock()

    def enforce(self, key: str) -> None:
        """Record a hit for ``key`` raising if the limit is exceeded."""

        now = monotonic()
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            bucket.append(now)

    def reset(self) -> None:
        """Clear all stored hit counters."""

        with self._lock:
            self._hits.clear()


_RATE_LIMITER = RateLimiter(_RATE_LIMIT_CALLS, _RATE_LIMIT_WINDOW_SECONDS)


async def _enforce_rate_limit(
    request: Request,
    user: auth.User = Depends(require_permission("read")),
) -> auth.User:
    """Dependency enforcing per-user rate limits before returning ``user``."""

    identifier = user.username or "anonymous"
    key = f"{request.url.path}:{identifier}"
    _RATE_LIMITER.enforce(key)
    return user


_ROUTING_MODEL: ReviewerModel | None = None
_ROUTING_MODEL_LOCK = Lock()
_ROUTING_RECOMMEND_LOCK = asyncio.Lock()

_WARMED = False
_WARM_COUNT = 0
_WARM_LOCK = Lock()


def _get_reviewer_model() -> ReviewerModel:
    """Return a cached :class:`ReviewerModel` instance."""

    global _ROUTING_MODEL
    with _ROUTING_MODEL_LOCK:
        if _ROUTING_MODEL is None:
            _ROUTING_MODEL = ReviewerModel()
        return _ROUTING_MODEL


async def _recommend(text: str, top_k: int) -> Recommendation:
    """Serialise access to the routing model when generating recommendations."""

    model = _get_reviewer_model()
    async with _ROUTING_RECOMMEND_LOCK:
        return model.recommend(text, k=top_k)


def warm_ml_sessions() -> None:
    """Warm ONNX-backed model sessions once per process."""

    global _WARMED, _WARM_COUNT
    with _WARM_LOCK:
        if _WARMED:
            return
        try:
            quality_assessment("Warmup text for caching")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Quality critic warm-up failed: %s", exc)
        try:
            evaluate_compliance("Warmup text for caching")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Compliance classifier warm-up failed: %s", exc)
        try:
            get_signature_anomaly_metadata()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Signature anomaly warm-up failed: %s", exc)
        try:
            _get_reviewer_model()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Routing model warm-up failed: %s", exc)
        _WARMED = True
        _WARM_COUNT += 1


def warmup_count() -> int:
    """Return the number of times :func:`warm_ml_sessions` performed work."""

    return _WARM_COUNT


def reset_warm_state_for_testing() -> None:
    """Reset warm-up tracking and cached reviewer model for tests."""

    global _WARMED, _WARM_COUNT, _ROUTING_MODEL
    with _WARM_LOCK:
        _WARMED = False
        _WARM_COUNT = 0
    with _ROUTING_MODEL_LOCK:
        _ROUTING_MODEL = None


def reset_rate_limiter_for_testing() -> None:
    """Clear stored rate limiting counters (used by unit tests)."""

    _RATE_LIMITER.reset()


class QualityAssessmentRequest(BaseModel):
    """Payload for requesting a quality assessment."""

    text: str = Field(..., min_length=1)
    doc_type: str | None = Field(default=None, description="Document type context")
    document_id: str | None = Field(default=None, description="Associated document identifier")


class QualityAssessmentResponse(BaseModel):
    """Structured response for quality assessments."""

    score: float
    raw_score: float
    flags: dict[str, float]
    high_risk_terms: list[str]


class ComplianceEvaluationRequest(BaseModel):
    """Payload for compliance probability evaluation."""

    text: str = Field(..., min_length=1)
    metadata: Mapping[str, float] | None = None
    document_id: str | None = Field(default=None)


class ComplianceEvaluationResponse(BaseModel):
    """Response model summarising compliance classifier output."""

    probability: float
    failing_rules: list[str]
    features: dict[str, float]
    source: str


class RoutingRecommendationRequest(BaseModel):
    """Payload requesting reviewer routing recommendations."""

    text: str = Field(..., min_length=1)
    top_k: int = Field(3, ge=1, le=10)
    document_id: str | None = Field(default=None)


class ReviewerScore(BaseModel):
    """Reviewer ranking entry."""

    reviewer: str
    probability: float


class RoutingRecommendationResponse(BaseModel):
    """Response containing routing recommendations."""

    approval_likelihood: float
    reviewers: list[ReviewerScore]


FeatureVector = conlist(
    float,
    min_length=len(SIGNATURE_ANOMALY_FEATURE_NAMES),
    max_length=len(SIGNATURE_ANOMALY_FEATURE_NAMES),
)


class SignatureAnomalyRequest(BaseModel):
    """Payload describing signature anomaly telemetry."""

    features: FeatureVector
    document_id: str | None = Field(default=None)


class SignatureAnomalyResponse(BaseModel):
    """Response summarising the anomaly score and model metadata."""

    score: float
    model_version: str | None
    sha256: str
    model_path: str
    metadata: Mapping[str, str]


@router.post("/quality", response_model=QualityAssessmentResponse)
@log_call
async def quality_endpoint(
    payload: QualityAssessmentRequest,
    user: auth.User = Depends(_enforce_rate_limit),
) -> QualityAssessmentResponse:
    """Return an approval quality assessment for the provided text."""

    assessment = quality_assessment(payload.text, doc_type=payload.doc_type)
    warnings = high_risk_warnings(payload.text)
    flags = {name: float(value) for name, value in zip(QUALITY_FLAG_NAMES, assessment.flags)}
    log_audit_event(
        payload.document_id or "ml::quality",
        "ml_quality_assessment",
        actor=user.username,
        doc_type=payload.doc_type,
        score=assessment.score,
        raw_score=assessment.raw_score,
        high_risk_terms=list(warnings),
    )
    return QualityAssessmentResponse(
        score=assessment.score,
        raw_score=assessment.raw_score,
        flags=flags,
        high_risk_terms=warnings,
    )


@router.post("/compliance", response_model=ComplianceEvaluationResponse)
@log_call
async def compliance_endpoint(
    payload: ComplianceEvaluationRequest,
    user: auth.User = Depends(_enforce_rate_limit),
) -> ComplianceEvaluationResponse:
    """Return compliance likelihood and triggered rules for ``text``."""

    result = evaluate_compliance(payload.text, payload.metadata)
    log_audit_event(
        payload.document_id or "ml::compliance",
        "ml_compliance_evaluation",
        actor=user.username,
        probability=result.probability,
        source=result.source,
        failing_rules=list(result.failing_rules),
    )
    return ComplianceEvaluationResponse(
        probability=result.probability,
        failing_rules=list(result.failing_rules),
        features=dict(result.features),
        source=result.source,
    )


@router.post("/routing", response_model=RoutingRecommendationResponse)
@log_call
async def routing_endpoint(
    payload: RoutingRecommendationRequest,
    user: auth.User = Depends(_enforce_rate_limit),
) -> RoutingRecommendationResponse:
    """Return reviewer routing recommendations based on ``text``."""

    recommendation = await _recommend(payload.text, payload.top_k)
    reviewer_entries = [
        ReviewerScore(reviewer=name, probability=float(probability))
        for name, probability in recommendation.ranked_reviewers
    ]
    log_audit_event(
        payload.document_id or "ml::routing",
        "ml_routing_recommendation",
        actor=user.username,
        top_k=payload.top_k,
        approval_likelihood=recommendation.approval_likelihood,
        reviewers=[entry.reviewer for entry in reviewer_entries],
    )
    return RoutingRecommendationResponse(
        approval_likelihood=recommendation.approval_likelihood,
        reviewers=reviewer_entries,
    )


@router.post("/signature", response_model=SignatureAnomalyResponse)
@log_call
async def signature_endpoint(
    payload: SignatureAnomalyRequest,
    user: auth.User = Depends(_enforce_rate_limit),
) -> SignatureAnomalyResponse:
    """Return anomaly score for signature telemetry features."""

    score, metadata = score_signature_anomaly(payload.features)
    log_audit_event(
        payload.document_id or "ml::signature",
        "ml_signature_anomaly",
        actor=user.username,
        score=score,
        model_version=metadata.version,
    )
    return SignatureAnomalyResponse(
        score=score,
        model_version=metadata.version,
        sha256=metadata.sha256,
        model_path=str(metadata.path),
        metadata=dict(metadata.custom_metadata),
    )


__all__ = [
    "router",
    "warm_ml_sessions",
    "warmup_count",
    "reset_rate_limiter_for_testing",
    "reset_warm_state_for_testing",
]
