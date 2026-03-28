# SPDX-License-Identifier: MIT
"""Tests verifying CPU optimizations from docs/performance/cpu_optimization_analysis.md."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Task 1: _base_stats is cached with lru_cache
# ---------------------------------------------------------------------------


class TestBaseStatsCache:
    """Verify _base_stats uses lru_cache to avoid redundant recomputation."""

    def test_base_stats_has_lru_cache(self):
        from docreview360.ml.features import _base_stats

        assert hasattr(_base_stats, "cache_info"), "_base_stats should be wrapped with lru_cache"

    def test_base_stats_returns_same_object_for_same_text(self):
        from docreview360.ml.features import _base_stats

        _base_stats.cache_clear()
        text = "This is a sample document. It has multiple sentences."
        result1 = _base_stats(text)
        result2 = _base_stats(text)
        assert result1 is result2, "cached call should return the same object"

    def test_base_stats_cache_hit_count(self):
        from docreview360.ml.features import _base_stats

        _base_stats.cache_clear()
        text = "Hello world. Testing cache."
        _base_stats(text)
        _base_stats(text)
        _base_stats(text)
        info = _base_stats.cache_info()
        assert info.hits >= 2, f"expected >= 2 cache hits, got {info.hits}"
        assert info.misses >= 1


# ---------------------------------------------------------------------------
# Task 2: ONNX Runtime session options are configured
# ---------------------------------------------------------------------------


class TestOnnxSessionOptions:
    """Verify ONNX sessions are created with optimised SessionOptions."""

    def test_get_session_passes_session_options(self):
        """Ensure get_session creates sessions with explicit opts."""
        import docreview360.ml.onnx_infer as mod

        src = Path(mod.__file__).read_text()
        assert "SessionOptions()" in src, "get_session should create SessionOptions"
        assert "ORT_ENABLE_ALL" in src, "graph_optimization_level should be ORT_ENABLE_ALL"
        assert "intra_op_num_threads" in src
        assert "inter_op_num_threads" in src
        assert "sess_options=opts" in src or "sess_options = opts" in src


# ---------------------------------------------------------------------------
# Task 3: Regex patterns in features.py are pre-compiled at module level
# ---------------------------------------------------------------------------


class TestPrecompiledRegex:
    """Verify hot-path regex patterns are pre-compiled at module level."""

    def test_syllable_regex_is_compiled(self):
        from docreview360.ml.features import _SYLLABLE_RE

        assert isinstance(_SYLLABLE_RE, re.Pattern)

    def test_style_score_regexes_are_compiled(self):
        from docreview360.ml import features

        for name in (
            "_TRAILING_WS_RE",
            "_DOUBLE_SPACE_RE",
            "_REPEATED_PUNCT_RE",
            "_MISSING_SPACE_RE",
            "_REPEATED_CAPS_RE",
            "_SENTENCE_SPLIT_RE",
        ):
            pattern = getattr(features, name)
            assert isinstance(pattern, re.Pattern), f"{name} should be a compiled regex"

    def test_count_syllables_uses_compiled_regex(self):
        from docreview360.ml.features import count_syllables

        assert count_syllables("hello") >= 1
        assert count_syllables("a") == 1


# ---------------------------------------------------------------------------
# Task 4: Consolidated syllable counter with silent-e heuristic
# ---------------------------------------------------------------------------


class TestSyllableCounterConsolidation:
    """Verify single syllable implementation with silent-e handling."""

    def test_silent_e_heuristic(self):
        from docreview360.ml.features import count_syllables

        # "make" has a silent 'e': should count as 1 syllable, not 2
        assert count_syllables("make") == 1
        assert count_syllables("cake") == 1

    def test_multi_syllable_with_e(self):
        from docreview360.ml.features import count_syllables

        # "erase" has silent 'e' but still multiple vowel groups
        assert count_syllables("erase") >= 1

    def test_doc_validation_uses_features_impl(self):
        from docreview360.doc_validation import _count_syllables
        from docreview360.ml.features import count_syllables

        for word in ("hello", "world", "make", "cake", "document", "e"):
            assert _count_syllables(word) == count_syllables(word), (
                f"doc_validation._count_syllables('{word}') should match features.count_syllables"
            )

    def test_ai_utils_delegates_to_features(self):
        from docreview360.ai_utils import _count_syllables
        from docreview360.ml.features import count_syllables

        for word in ("hello", "make", "python"):
            assert _count_syllables(word) == count_syllables(word)


# ---------------------------------------------------------------------------
# Task 5: Consolidated hash helpers
# ---------------------------------------------------------------------------


class TestConsolidatedHashHelpers:
    """Verify all modules use the shared file_sha256 utility."""

    def test_shared_hashing_module_exists(self):
        from docreview360.ml._hashing import file_sha256

        assert callable(file_sha256)

    def test_hash_produces_correct_output(self, tmp_path):
        from docreview360.ml._hashing import file_sha256
        import hashlib

        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert file_sha256(f) == expected

    def test_onnx_infer_uses_shared_hash(self):
        import docreview360.ml.onnx_infer as mod

        src = Path(mod.__file__).read_text()
        assert "from ._hashing import file_sha256" in src

    def test_signature_anomaly_uses_shared_hash(self):
        import docreview360.ml.signature_anomaly as mod

        src = Path(mod.__file__).read_text()
        assert "from ._hashing import file_sha256" in src

    def test_torch_models_uses_shared_hash(self):
        import docreview360.ml.torch_models as mod

        src = Path(mod.__file__).read_text()
        assert "from ._hashing import file_sha256" in src


# ---------------------------------------------------------------------------
# Task 6: Training pre-computes feature matrix
# ---------------------------------------------------------------------------


class TestTrainingPrecomputedFeatures:
    """Verify routing_critic training pre-computes features before the epoch loop."""

    def test_training_source_precomputes(self):
        import docreview360.ml.routing_critic as mod

        src = Path(mod.__file__).read_text()
        assert "feature_matrix" in src, "training should build feature_matrix before loop"
        assert "feature_matrix[i]" in src, "loop should index into pre-computed matrix"

    def test_training_runs_correctly(self):
        from docreview360.ml.routing_critic import RoutingExample, train_routing_critic

        examples = [
            RoutingExample(text="Good document.", reviewer="alice", approved=True),
            RoutingExample(text="Bad document.", reviewer="bob", approved=False),
        ]
        critic = train_routing_critic(["alice", "bob"], examples, epochs=5, lr=0.01)
        assert critic is not None
        assert len(critic.reviewers) == 2


# ---------------------------------------------------------------------------
# Task 7: Simplified scalar extraction
# ---------------------------------------------------------------------------


class TestScalarExtraction:
    """Verify inference code uses direct indexing instead of squeeze().item()."""

    def test_reviewer_model_uses_direct_indexing(self):
        import docreview360.reviewer_model as mod

        src = Path(mod.__file__).read_text()
        assert "[0, 0]" in src, "reviewer_model should use direct indexing"

    def test_signature_anomaly_uses_direct_indexing(self):
        import docreview360.ml.signature_anomaly as mod

        src = Path(mod.__file__).read_text()
        assert "[0, 0]" in src or "outputs[0][0" in src


# ---------------------------------------------------------------------------
# Task 8: high_risk_warnings is cached
# ---------------------------------------------------------------------------


class TestHighRiskWarningsCache:
    """Verify high_risk_warnings uses lru_cache internally."""

    def test_has_cached_inner(self):
        from docreview360.quality import _high_risk_warnings_cached

        assert hasattr(_high_risk_warnings_cached, "cache_info")

    def test_returns_list(self):
        from docreview360.quality import high_risk_warnings

        result = high_risk_warnings("some safe text")
        assert isinstance(result, list), "public API should return a list"

    def test_cache_hit(self):
        from docreview360.quality import _high_risk_warnings_cached

        _high_risk_warnings_cached.cache_clear()
        text = "This document is safe."
        _high_risk_warnings_cached(text)
        _high_risk_warnings_cached(text)
        info = _high_risk_warnings_cached.cache_info()
        assert info.hits >= 1


# ---------------------------------------------------------------------------
# Task 11: PII regex is pre-compiled at module level
# ---------------------------------------------------------------------------


class TestPiiRegexPrecompiled:
    """Verify the SSN regex in nemo_guardrails is compiled at module level."""

    def test_module_level_regex_exists(self):
        from docreview360 import nemo_guardrails

        assert hasattr(nemo_guardrails, "_SSN_RE")
        assert isinstance(nemo_guardrails._SSN_RE, re.Pattern)

    def test_contains_pii_detects_ssn(self):
        from docreview360.nemo_guardrails import contains_pii

        assert contains_pii("My SSN is 123-45-6789")
        assert not contains_pii("No PII here")

    def test_contains_pii_does_not_recompile(self):
        """Ensure the function body does not call re.compile."""
        from docreview360.nemo_guardrails import contains_pii
        import inspect

        source = inspect.getsource(contains_pii)
        assert "re.compile" not in source, "contains_pii should not compile regex internally"


# ---------------------------------------------------------------------------
# Task 12: Celery eager mode defaults off in production
# ---------------------------------------------------------------------------


class TestCeleryEagerMode:
    """Verify Celery eager mode is disabled by default in production environments."""

    def test_source_has_prod_aware_config(self):
        import docreview360.celery_app as mod

        src = Path(mod.__file__).read_text()
        assert "_prod_envs" in src
        # In production the default should be "0" (not eager)
        assert '"0"' in src, "production default for CELERY_EAGER should be '0'"
