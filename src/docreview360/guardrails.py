# SPDX-License-Identifier: MIT
"""Shared guardrail policy helpers built around ONNX critic outputs."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Mapping

from .ml.compliance_classifier import ComplianceClassification, evaluate_compliance
from .quality import QUALITY_FLAG_NAMES, QualityAssessment, quality_assessment
from .settings_manager import load_settings

__all__ = [
    "GuardrailDiagnostics",
    "GuardrailThresholds",
    "evaluate_guardrails",
    "guardrail_quality_assessment",
    "load_guardrail_thresholds",
]


@dataclass(frozen=True)
class GuardrailThresholds:
    """Configuration values controlling quality and compliance guardrails."""

    min_quality_score: float = 0.8
    quality_flag_threshold: float = 0.85
    min_compliance_probability: float = 0.25
    auto_assign_editor: str | None = None
    auto_assign_quality_below: float | None = None
    auto_assign_compliance_below: float | None = None

    def overridden(self, **kwargs: Any) -> "GuardrailThresholds":
        """Return a copy with ``kwargs`` applied."""

        return replace(self, **kwargs)


@dataclass(frozen=True)
class GuardrailDiagnostics:
    """Result payload returned by :func:`evaluate_guardrails`."""

    thresholds: GuardrailThresholds
    quality: QualityAssessment
    compliance: ComplianceClassification
    triggered_flags: tuple[str, ...]
    blocked: bool
    auto_assign_editor: str | None

    def asdict(self) -> dict[str, Any]:
        """Return a serialisable representation of the diagnostics."""

        flags = dict(zip(QUALITY_FLAG_NAMES, self.quality.flags))
        compliance = {
            "probability": self.compliance.probability,
            "failing_rules": list(self.compliance.failing_rules),
            "features": dict(self.compliance.features),
            "source": self.compliance.source,
        }
        return {
            "blocked": self.blocked,
            "passed": not self.blocked,
            "triggered_flags": list(self.triggered_flags),
            "auto_assign_editor": self.auto_assign_editor,
            "quality": {
                "score": self.quality.score,
                "raw_score": self.quality.raw_score,
                "flags": flags,
            },
            "compliance": compliance,
            "thresholds": {
                "min_quality_score": self.thresholds.min_quality_score,
                "quality_flag_threshold": self.thresholds.quality_flag_threshold,
                "min_compliance_probability": self.thresholds.min_compliance_probability,
                "auto_assign_editor": self.thresholds.auto_assign_editor,
                "auto_assign_quality_below": self.thresholds.auto_assign_quality_below,
                "auto_assign_compliance_below": self.thresholds.auto_assign_compliance_below,
            },
        }


def _ensure_mapping(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _coerce_float(mapping: Mapping[str, Any], *candidates: str) -> float | None:
    for key in candidates:
        if key not in mapping:
            continue
        try:
            raw = mapping[key]
            if isinstance(raw, bool):
                continue
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        return value
    return None


def _normalize_probability(value: float | None, default: float) -> float:
    if value is None or not 0 <= value <= 1:
        return default
    return value


def _coerce_str(mapping: Mapping[str, Any], *candidates: str) -> str | None:
    for key in candidates:
        value = mapping.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def guardrail_quality_assessment(text: str) -> QualityAssessment:
    """Return a quality assessment falling back to heuristics when needed."""

    return quality_assessment(text)


def load_guardrail_thresholds(  # noqa: C901
    settings: Mapping[str, Any] | None = None,
) -> GuardrailThresholds:
    """Return configured guardrail thresholds or sensible defaults."""

    if settings is None:
        settings = load_settings()

    documents_cfg = _ensure_mapping(settings.get("documents"))
    guardrail_cfg = _ensure_mapping(documents_cfg.get("guardrails"))

    quality_cfg = _ensure_mapping(guardrail_cfg.get("quality"))
    compliance_cfg = _ensure_mapping(guardrail_cfg.get("compliance"))
    auto_cfg = _ensure_mapping(guardrail_cfg.get("auto_assign"))

    defaults = GuardrailThresholds()

    min_quality_score = _coerce_float(
        quality_cfg,
        "min_score",
        "minimum_score",
        "threshold",
    )
    if min_quality_score is None:
        min_quality_score = _coerce_float(guardrail_cfg, "quality_min_score")
    min_quality_score = _normalize_probability(min_quality_score, defaults.min_quality_score)

    quality_flag_threshold = _coerce_float(
        quality_cfg,
        "flag_threshold",
        "flag_limit",
    )
    if quality_flag_threshold is None:
        quality_flag_threshold = _coerce_float(guardrail_cfg, "quality_flag_threshold")
    quality_flag_threshold = _normalize_probability(
        quality_flag_threshold, defaults.quality_flag_threshold
    )

    min_compliance_probability = _coerce_float(
        compliance_cfg,
        "min_probability",
        "threshold",
    )
    if min_compliance_probability is None:
        min_compliance_probability = _coerce_float(
            guardrail_cfg,
            "compliance_min_probability",
        )
    min_compliance_probability = _normalize_probability(
        min_compliance_probability, defaults.min_compliance_probability
    )

    auto_assign_editor = _coerce_str(auto_cfg, "editor", "assignee")
    if auto_assign_editor is None:
        auto_assign_editor = _coerce_str(guardrail_cfg, "auto_assign_editor")

    auto_quality = _coerce_float(auto_cfg, "quality_below", "quality_under")
    if auto_quality is None:
        auto_quality = _coerce_float(guardrail_cfg, "auto_assign_quality_below")
    if auto_quality is not None and not 0 <= auto_quality <= 1:
        auto_quality = None

    auto_compliance = _coerce_float(auto_cfg, "compliance_below", "compliance_under")
    if auto_compliance is None:
        auto_compliance = _coerce_float(guardrail_cfg, "auto_assign_compliance_below")
    if auto_compliance is not None and not 0 <= auto_compliance <= 1:
        auto_compliance = None

    return GuardrailThresholds(
        min_quality_score=min_quality_score,
        quality_flag_threshold=quality_flag_threshold,
        min_compliance_probability=min_compliance_probability,
        auto_assign_editor=auto_assign_editor,
        auto_assign_quality_below=auto_quality,
        auto_assign_compliance_below=auto_compliance,
    )


def _auto_assign_editor(
    thresholds: GuardrailThresholds,
    quality: QualityAssessment,
    compliance: ComplianceClassification,
    blocked: bool,
) -> str | None:
    if blocked or not thresholds.auto_assign_editor:
        return None

    quality_trigger = (
        thresholds.auto_assign_quality_below is not None
        and quality.score < thresholds.auto_assign_quality_below
    )
    compliance_trigger = (
        thresholds.auto_assign_compliance_below is not None
        and compliance.probability < thresholds.auto_assign_compliance_below
    )
    if quality_trigger or compliance_trigger:
        return thresholds.auto_assign_editor
    return None


def evaluate_guardrails(
    text: str,
    *,
    thresholds: GuardrailThresholds | None = None,
) -> GuardrailDiagnostics:
    """Evaluate quality/compliance guardrails for ``text``."""

    thresholds = thresholds or load_guardrail_thresholds()
    quality = guardrail_quality_assessment(text)
    compliance = evaluate_compliance(text)

    triggered = tuple(
        name
        for name, value in zip(QUALITY_FLAG_NAMES, quality.flags)
        if value >= thresholds.quality_flag_threshold
    )

    blocked = not text.strip() or quality.score < thresholds.min_quality_score
    blocked = blocked or bool(triggered)
    if compliance.source == "onnx":
        blocked = blocked or compliance.probability < thresholds.min_compliance_probability

    auto_assign = _auto_assign_editor(thresholds, quality, compliance, blocked)

    return GuardrailDiagnostics(
        thresholds=thresholds,
        quality=quality,
        compliance=compliance,
        triggered_flags=triggered,
        blocked=blocked,
        auto_assign_editor=auto_assign,
    )
