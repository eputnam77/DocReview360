"""Feature adapters centralising heuristics for DocReview360 models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import re
import tempfile
from typing import Any, Callable, Mapping, Sequence

try:  # pragma: no cover - optional dependency wiring
    from govdocverify.cli import process_document as _gov_run  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - runtime fallback
    _gov_run = None

__all__ = [
    "CUSTOM_STYLE_RULES",
    "FEATURE_SCHEMA_REGISTRY",
    "FANN_FEATURE_NAMES",
    "SIGNATURE_ANOMALY_FEATURE_NAMES",
    "SchemaVersion",
    "compliance_features",
    "count_syllables",
    "quality_features",
    "routing_features",
    "signature_features",
    "structural_pattern_score",
    "style_guide_score",
]


@dataclass(frozen=True)
class SchemaVersion:
    """Metadata describing a serialised feature payload."""

    version: str
    schema_path: str


FANN_FEATURE_NAMES: tuple[str, ...] = (
    "length",
    "unique_ratio",
    "repeated",
    "readability",
    "style",
    "structure",
)


FEATURE_SCHEMA_REGISTRY: dict[str, SchemaVersion] = {
    "quality": SchemaVersion("1.0.0", "docs/ml/quality_features.schema.json"),
    "compliance": SchemaVersion("1.0.0", "docs/ml/compliance_features.schema.json"),
    "routing": SchemaVersion("1.0.0", "docs/ml/routing_features.schema.json"),
    "signature": SchemaVersion("1.1.0", "docs/ml/signature_features.schema.json"),
}

_CUSTOM_STYLE_RULES: list[Callable[[str], bool]] = []
_MAX_SENT_LEN = 120


def register_style_rule(rule: Callable[[str], bool]) -> None:
    """Register an additional style rule used by the heuristic scorer."""

    _CUSTOM_STYLE_RULES.append(rule)


CUSTOM_STYLE_RULES = _CUSTOM_STYLE_RULES


_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _tokenise(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def count_syllables(word: str) -> int:
    """Rough syllable estimator used for readability features."""

    groups = re.findall(r"[aeiouy]+", word.lower())
    return max(1, len(groups))


def _heuristic_style_score(text: str) -> float:
    sentences_raw = re.findall(r".*?[.!?](?:\s|$)", text, re.S) or [text]
    good = 0
    for raw in sentences_raw:
        if not raw.strip():
            continue
        lines = raw.splitlines()
        trailing_ws = any(re.search(r"[ \t]+$", line) for line in lines)
        s = raw.strip()
        words = s.split()
        has_repeat = any(w1.lower() == w2.lower() for w1, w2 in zip(words, words[1:]))
        missing_space = re.search(r"[;,](?!\s)", s)
        repeated_caps = re.search(r"[A-Z]{2,}[a-z]", s)
        passes_base = (
            s[0].isupper()
            and s[-1] in ".!?"
            and not re.search(r"\s{2,}", s)
            and not re.search(r"[.!?]{2,}", s)
            and not has_repeat
            and not missing_space
            and not trailing_ws
            and not repeated_caps
            and len(s) <= _MAX_SENT_LEN
        )
        passes_custom = all(rule(s) for rule in CUSTOM_STYLE_RULES)
        if passes_base and passes_custom:
            good += 1
    return good / len(sentences_raw)


def style_guide_score(text: str) -> float:
    """Return a style score using GovDocVerify when available; fall back otherwise."""

    if _gov_run is not None:
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tmp:
                tmp.write(text)
                tmp.flush()
                path = tmp.name
            try:
                result = _gov_run(path, "Other")
            finally:
                os.unlink(path)
            issues = result.get("styleIssues", [])  # type: ignore[assignment]
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            total = len(sentences) or 1
            return max(0.0, 1 - len(issues) / total)
        except Exception:
            pass
    return _heuristic_style_score(text)


def structural_pattern_score(text: str) -> float:
    """Return a ratio of structural lines to total lines with a heading-order penalty."""

    lines = text.splitlines()
    if not lines:
        return 0.0
    headings: list[int] = []
    bullets = 0
    numbered = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            m = re.match(r"(#+)\s", stripped)
            if m:
                headings.append(len(m.group(1)))
        elif stripped.startswith(("-", "*", "+")):
            bullets += 1
        elif re.match(r"\d+[.)]\s", stripped):
            numbered += 1
    structured = len(headings) + bullets + numbered
    base = structured / len(lines)
    if not headings:
        return base
    jumps = sum(1 for a, b in zip(headings, headings[1:]) if b > a + 1)
    penalty = jumps / len(headings)
    return base * (1 - penalty)


@dataclass(frozen=True)
class _BaseStats:
    length_norm: float
    unique_ratio: float
    duplicate_ratio: float
    readability_norm: float
    readability_raw: float
    style: float
    structure: float
    fann_vector: tuple[float, ...]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _metadata_completeness(metadata: Mapping[str, Any] | None) -> float:
    if not metadata:
        return 0.0
    total = len(metadata)
    if total == 0:
        return 0.0
    filled = 0
    for value in metadata.values():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, tuple, set)) and not value:
            continue
        filled += 1
    return _clamp(filled / total)


def _base_stats(text: str) -> _BaseStats:
    words = _tokenise(text)
    repeated = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
    unique_ratio = len(set(words)) / (len(words) or 1)
    sentence_count = sum(text.count(ch) for ch in ".!?") or 1
    word_count = len(words) or 1
    syllables = sum(count_syllables(w) for w in words) or 1
    words_per_sentence = word_count / sentence_count
    syllables_per_word = syllables / word_count
    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    readability_raw = flesch / 100
    readability_norm = _clamp(readability_raw)
    style = _clamp(style_guide_score(text))
    structure = _clamp(structural_pattern_score(text))
    length_norm = _clamp(len(text) / 2000)
    duplicate_ratio = _clamp(repeated / (len(words) - 1 or 1))
    fann_vector = (
        len(text) / 1000,
        unique_ratio,
        float(repeated),
        readability_raw,
        style,
        structure,
    )
    return _BaseStats(
        length_norm=length_norm,
        unique_ratio=unique_ratio,
        duplicate_ratio=duplicate_ratio,
        readability_norm=readability_norm,
        readability_raw=readability_raw,
        style=style,
        structure=structure,
        fann_vector=fann_vector,
    )


def _round_features(data: Mapping[str, float]) -> dict[str, float]:
    return {key: round(float(value), 6) for key, value in data.items()}


def _payload(name: str, features: Mapping[str, float], legacy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    info = FEATURE_SCHEMA_REGISTRY[name]
    payload: dict[str, Any] = {
        "version": info.version,
        "features": _round_features(features),
    }
    if legacy:
        payload["legacy"] = legacy
    return payload


def quality_features(text: str, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return normalized quality features with legacy FANN mapping."""

    stats = _base_stats(text)
    features: dict[str, float] = {
        "length": stats.length_norm,
        "vocabulary_diversity": stats.unique_ratio,
        "duplicate_ratio": stats.duplicate_ratio,
        "readability": stats.readability_norm,
        "style": stats.style,
        "structure": stats.structure,
    }
    if metadata:
        features["metadata_completeness"] = _metadata_completeness(metadata)
    legacy = {
        "fann": {
            name: round(float(value), 6)
            for name, value in zip(FANN_FEATURE_NAMES, stats.fann_vector)
        }
    }
    return _payload("quality", features, legacy)


def compliance_features(text: str, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return compliance-centric features using readability, structure, and metadata heuristics."""

    stats = _base_stats(text)
    metadata_score = _metadata_completeness(metadata)
    compliance_risk = 1 - min(stats.readability_norm, stats.structure, metadata_score or 0.0)
    features = {
        "readability": stats.readability_norm,
        "structure": stats.structure,
        "metadata_completeness": metadata_score,
        "style": stats.style,
        "compliance_risk": _clamp(compliance_risk),
    }
    return _payload("compliance", features)


def routing_features(text: str, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return routing features guiding workflow prioritisation."""

    stats = _base_stats(text)
    metadata_score = _metadata_completeness(metadata)
    priority = _clamp(0.5 * stats.length_norm + 0.3 * (1 - stats.readability_norm) + 0.2 * metadata_score)
    features = {
        "content_size": stats.length_norm,
        "novelty": stats.unique_ratio,
        "duplication": stats.duplicate_ratio,
        "structure": stats.structure,
        "priority": priority,
        "metadata_signal": metadata_score,
    }
    return _payload("routing", features)


def _serialise_chain(chain: Sequence[bytes | str] | None) -> list[bytes]:
    items: list[bytes] = []
    if not chain:
        return items
    for entry in chain:
        if entry is None:  # pragma: no cover - defensive
            continue
        if isinstance(entry, bytes):
            items.append(entry)
        else:
            items.append(entry.encode("utf-8"))
    return items


def _certificate_attributes(chain: Sequence[bytes | str] | None) -> tuple[float, float, float]:
    chain_bytes = _serialise_chain(chain)
    if not chain_bytes:
        return 0.0, 0.0, 0.0

    depth = _clamp(len(chain_bytes) / 5.0)
    validity = 0.0
    entropy = 0.0
    try:
        from cryptography import x509  # local import to keep module importable without dependency

        raw = chain_bytes[0]
        try:
            cert = x509.load_pem_x509_certificate(raw)
        except ValueError:
            cert = x509.load_der_x509_certificate(raw)

        not_after = getattr(cert, "not_valid_after_utc", None) or cert.not_valid_after
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)
        remaining = (not_after - datetime.now(timezone.utc)).total_seconds()
        if remaining > 0:
            validity = _clamp(remaining / (365 * 24 * 3600))
        subject = cert.subject.rfc4514_string()
        if subject:
            entropy = _clamp(len(set(subject)) / 64.0)
    except Exception:
        # If the certificate payload cannot be parsed we fall back to depth-only
        pass
    return depth, validity, entropy


def _retry_stats(retries: Mapping[str, Any] | None) -> tuple[float, float]:
    if not retries:
        return 0.0, 0.0
    retry_attempts = float(retries.get("retry", 0.0) or 0.0)
    exhausted_attempts = float(retries.get("exhausted", 0.0) or 0.0)
    total = max(retry_attempts + exhausted_attempts, 0.0)
    ratio = _clamp(total / (total + 5.0))
    exhaustion = _clamp(exhausted_attempts / (total + 1.0))
    return ratio, exhaustion


def signature_features(
    text: str,
    metadata: Mapping[str, Any] | None = None,
    *,
    verification_duration: float | None = None,
    retries: Mapping[str, Any] | None = None,
    certificate_chain: Sequence[bytes | str] | None = None,
) -> dict[str, Any]:
    """Return signature verification features combining heuristics and runtime signals."""

    stats = _base_stats(text)
    metadata_score = _metadata_completeness(metadata)
    metadata_density = _clamp(len(metadata or {}) / 10.0)
    has_certificate = 1.0 if metadata and metadata.get("certificate_url") else 0.0
    has_hash = 1.0 if metadata and metadata.get("hash") else 0.0
    has_timestamp = 1.0 if metadata and metadata.get("verified_at") else 0.0
    evidence_strength = _clamp(0.4 * has_certificate + 0.3 * has_hash + 0.3 * has_timestamp)
    duration_norm = _clamp((verification_duration or 0.0) / 10.0)
    retry_ratio, retry_exhaustion = _retry_stats(retries)
    cert_depth, cert_validity, cert_entropy = _certificate_attributes(certificate_chain)

    features = {
        "structure": stats.structure,
        "readability": stats.readability_norm,
        "metadata_completeness": metadata_score,
        "evidence_strength": evidence_strength,
        "verification_duration": duration_norm,
        "retry_ratio": retry_ratio,
        "retry_exhaustion": retry_exhaustion,
        "certificate_depth": cert_depth,
        "certificate_validity": cert_validity,
        "certificate_subject_entropy": cert_entropy,
        "metadata_density": metadata_density,
    }
    return _payload("signature", features)
SIGNATURE_ANOMALY_FEATURE_NAMES: tuple[str, ...] = (
    "verification_duration",
    "metadata_completeness",
    "retry_ratio",
    "retry_exhaustion",
    "certificate_depth",
    "certificate_validity",
    "certificate_subject_entropy",
    "metadata_density",
)
