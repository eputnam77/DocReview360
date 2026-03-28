# CPU Optimization Analysis

> **Date:** 2026-03-28
> **Scope:** Backend ML inference pipeline, feature extraction, and frontend render paths
> **Goal:** Identify low-effort, high-impact CPU savings without changing the process workflow

---

## Executive Summary

The DocReview360 inference pipeline is well-structured but leaves meaningful CPU cycles
on the table in three categories:

1. **Redundant recomputation** of text features across the quality/compliance/routing pipeline
2. **Untuned ONNX Runtime sessions** running with default (suboptimal) CPU settings
3. **Uncompiled regex and per-word overhead** in the hot feature-extraction path

None of the items below require architectural changes. Most are targeted one-file edits.

---

## 1. Redundant `_base_stats` Computation (HIGH impact)

**Location:** `src/docreview360/ml/features.py:255`

`_base_stats(text)` is the most expensive pure-Python function in the pipeline. It
tokenises the entire document, counts syllables word-by-word, runs the style-guide
heuristic (which itself iterates every sentence with multiple regex searches), and
computes structural scores.

The problem: a single document passing through the guardrails pipeline triggers
`_base_stats` **at least 3 times** for the same text:

| Call site | Triggered by |
|---|---|
| `quality_features(text)` | `guardrails.evaluate_guardrails` -> `quality_assessment` |
| `compliance_features(text)` | `guardrails.evaluate_guardrails` -> `evaluate_compliance` |
| `routing_features(text)` | `reviewer_model.recommend` / `routing_critic` |
| `signature_features(text)` | `approvals/signatures.py` (when signatures are verified) |

Each call re-tokenises, re-counts syllables, and re-runs the style heuristic.

Additionally, within `quality.py` itself:
- `explain_score()` (line 215) calls `quality_features(text)` AND `quality_assessment(text)`,
  which internally calls `quality_features` again -- **double computation**.
- `quality_assessment()` (line 170) calls `high_risk_warnings(text)` even after
  `_fallback_quality_assessment` already called it (line 143) -- **double scan**.

**Recommendation:** Add an `@functools.lru_cache` on `_base_stats` keyed on a hash of
the text, or pass a shared `_BaseStats` object through the pipeline. A simple LRU cache
with `maxsize=32` would eliminate all redundant calls during a single request cycle
without any API changes:

```python
from functools import lru_cache

@lru_cache(maxsize=32)
def _base_stats(text: str) -> _BaseStats:
    ...
```

Because `_base_stats` is a pure function of `text`, this is safe. The cache should be
bounded (32 is plenty) to avoid unbounded memory growth on long-running workers.

**Estimated saving:** 2-3x reduction in feature-extraction CPU time per document.

---

## 2. ONNX Runtime Session Options Not Configured (HIGH impact)

**Location:** `src/docreview360/ml/onnx_infer.py:102`

Sessions are created with bare defaults:

```python
session = ort.InferenceSession(str(model_path), providers=resolved_providers)
```

ONNX Runtime's CPU execution provider benefits significantly from explicit configuration:

```python
opts = ort.SessionOptions()
opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
opts.intra_op_num_threads = os.cpu_count() or 4
opts.inter_op_num_threads = 1  # single-request; avoid thread contention
opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

session = ort.InferenceSession(str(model_path), sess_options=opts, providers=resolved_providers)
```

Key settings:

| Option | Default | Recommended | Why |
|---|---|---|---|
| `graph_optimization_level` | `ORT_ENABLE_BASIC` | `ORT_ENABLE_ALL` | Enables constant folding, node fusion, and layout optimisation |
| `intra_op_num_threads` | 0 (all cores) | `cpu_count()` | Make it explicit; avoids runtime detection overhead |
| `inter_op_num_threads` | 0 | 1 | Models are small; inter-op parallelism adds scheduling overhead with no benefit |
| `execution_mode` | `ORT_SEQUENTIAL` | `ORT_SEQUENTIAL` | Confirm sequential for small models to avoid thread pool overhead |

For the small models in this project (linear critics, tiny MLPs), `ORT_ENABLE_ALL` graph
optimisation is the biggest win -- it fuses operations and eliminates unnecessary copies.

**Estimated saving:** 10-30% faster per-inference call depending on model complexity.

---

## 3. Uncompiled Regex in Hot Loops (MEDIUM impact)

**Location:** `src/docreview360/ml/features.py:132-166`

### 3a. `count_syllables` uses `re.findall` with a string pattern

```python
def count_syllables(word: str) -> int:
    groups = re.findall(r"[aeiouy]+", word.lower())
    return max(1, len(groups))
```

This is called **once per word** in every document. `re.findall` with a string pattern
bypasses the compiled-regex cache on high-throughput paths because Python's internal
regex cache is limited to 512 entries and uses LRU eviction.

**Fix:** Pre-compile the pattern at module level:

```python
_SYLLABLE_RE = re.compile(r"[aeiouy]+")

def count_syllables(word: str) -> int:
    return max(1, len(_SYLLABLE_RE.findall(word.lower())))
```

### 3b. `_heuristic_style_score` compiles 4+ regex patterns per sentence

Lines 146-156 call `re.search(...)` with string-literal patterns inside a
per-sentence loop:

```python
for raw in sentences_raw:
    trailing_ws = any(re.search(r"[ \t]+$", line) for line in lines)
    ...
    and not re.search(r"\s{2,}", s)
    and not re.search(r"[.!?]{2,}", s)
```

Each of these hits the internal cache lookup. For a 50-sentence document that's 200+
cache lookups.

**Fix:** Pre-compile all patterns at module level:

```python
_TRAILING_WS_RE = re.compile(r"[ \t]+$")
_DOUBLE_SPACE_RE = re.compile(r"\s{2,}")
_REPEATED_PUNCT_RE = re.compile(r"[.!?]{2,}")
_MISSING_SPACE_RE = re.compile(r"[;,](?!\s)")
_REPEATED_CAPS_RE = re.compile(r"[A-Z]{2,}[a-z]")
```

**Estimated saving:** 15-25% faster `_base_stats` execution on longer documents.

---

## 4. Duplicate Syllable Counter Implementations (LOW-MEDIUM impact)

Three separate syllable-counting implementations exist:

| Location | Function |
|---|---|
| `ml/features.py:132` | `count_syllables(word)` |
| `doc_validation.py:176` | `_count_syllables(word)` |
| `ai_utils.py:38` | `_count_syllables(word)` (wrapper around features.py) |

`doc_validation.py` has its own implementation with slightly different logic (handles
silent trailing 'e'). This means documents processed through both the ML pipeline and
the plain-language scorer pay the syllable-counting cost twice with different algorithms.

**Recommendation:** Consolidate to a single implementation. If the silent-e heuristic
from `doc_validation.py` is preferred, move it into `ml/features.py` and import from
there. This eliminates duplicate work when both paths process the same text.

---

## 5. Duplicate `_file_sha256` / `_hash_file` Functions (LOW impact, easy fix)

Two identical 8KB-chunk SHA-256 file hashers exist:

- `ml/onnx_infer.py:61` -- `_hash_file(path)`
- `quality.py:25` -- `_file_sha256(path)`

Also duplicated in `ml/torch_models.py:399` and `ml/signature_anomaly.py:76`.

**Recommendation:** Consolidate into one shared utility. Minor CPU saving but reduces
maintenance surface.

---

## 6. Training Recomputes Features Every Epoch (MEDIUM impact for training)

**Location:** `src/docreview360/ml/routing_critic.py:125-127`

```python
for _ in range(epochs):       # 200 epochs default
    for example in examples:
        features = routing_feature_vector(example.text, example.metadata)
```

`routing_feature_vector` calls `routing_features` which calls `_base_stats` -- the full
tokenisation + readability + style pipeline -- **every example, every epoch**. For 200
epochs and 100 examples, that's 20,000 calls to `_base_stats` when the text never changes.

**Fix:** Pre-compute the feature matrix once before the training loop:

```python
feature_matrix = np.array(
    [routing_feature_vector(ex.text, ex.metadata) for ex in examples],
    dtype=np.float32,
)
for _ in range(epochs):
    for i, example in enumerate(examples):
        features = feature_matrix[i]
        ...
```

**Estimated saving:** ~200x reduction in feature-extraction cost during training.

---

## 7. Scalar Extraction Overhead in Inference (LOW impact)

Throughout the inference pipeline, single-item results are extracted via a chain of
numpy operations:

```python
float(np.clip(outputs[0].squeeze().item(), 0.0, 1.0))
```

This pattern appears in:
- `quality.py:162` -- `score_arr.reshape(-1)[0]`
- `signature_anomaly.py:258` -- `outputs[0].squeeze().item()`
- `reviewer_model.py:268` -- `np.clip(approval_arr.squeeze().item(), 0.0, 1.0)`
- `compliance_classifier.py:176` -- `outputs.reshape(-1)[0].item()`

Each `.squeeze()`, `.reshape()`, `.item()` creates intermediate numpy objects.

**Recommendation:** Use direct indexing where possible:

```python
float(np.clip(outputs[0][0, 0], 0.0, 1.0))
```

This is a micro-optimisation but it's trivial to apply.

---

## 8. `high_risk_warnings` Redundant Tokenisation (LOW-MEDIUM impact)

**Location:** `src/docreview360/quality.py:104-117`

```python
def high_risk_warnings(text: str) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for word in re.findall(r"\b\w+\b", lower):
        if word in _HIGH_RISK_TERMS and word not in found:
            found.append(word)
    return found
```

This tokenises the entire document with regex. It's called:
- Once in `quality_assessment()` (line 170)
- Once in `_fallback_quality_assessment()` (line 143) when the ONNX model fails
- Once in `explain_score()` (line 232)
- Once from API routes

For the common success path in `quality_assessment`, the function is called once but the
document was already tokenised by `_base_stats` moments earlier.

**Recommendation:** Cache the result alongside `_base_stats`, or use `@lru_cache` with
the same bounded size. The `text.lower()` + `re.findall` scan on large documents is
non-trivial.

---

## 9. Frontend: Static TipTap Extension Imports (MEDIUM impact, build time + initial load)

**Location:** `frontend/pages/editors/tiptap.tsx`

All 25+ TipTap extensions are statically imported at the top of the editor page. On
CPU-constrained environments, this increases both build time and initial page hydration.

**Recommendation:** Use `next/dynamic` to lazy-load the editor component:

```tsx
const TiptapEditor = dynamic(() => import('../components/TiptapEditor'), {
  ssr: false,
  loading: () => <EditorSkeleton />,
});
```

This defers the CPU cost of loading and initialising 25+ ProseMirror extensions until
the user actually navigates to the editor.

---

## 10. Frontend: Dashboard Recharts Re-renders (LOW-MEDIUM impact)

**Location:** `frontend/pages/dashboard/index.tsx`, `admin.tsx`, `manager.tsx`

Dashboard pages compute chart data on every render. `computeDashboardData()` iterates
through project arrays multiple times.

**Recommendation:** Wrap chart data computation in `useMemo` with proper dependency
arrays. Wrap chart components in `React.memo` to prevent re-renders when parent state
changes but chart data has not.

---

## Summary Priority Matrix

| # | Issue | Effort | CPU Impact | Files Changed |
|---|---|---|---|---|
| 1 | Cache `_base_stats` | Small | **High** | `ml/features.py` |
| 2 | ONNX session options | Small | **High** | `ml/onnx_infer.py` |
| 3 | Pre-compile regex | Small | **Medium** | `ml/features.py` |
| 6 | Pre-compute training features | Small | **Medium** (training) | `ml/routing_critic.py` |
| 4 | Consolidate syllable counters | Small | **Low-Medium** | `ml/features.py`, `doc_validation.py`, `ai_utils.py` |
| 8 | Cache `high_risk_warnings` | Small | **Low-Medium** | `quality.py` |
| 9 | Lazy-load TipTap editor | Small | **Medium** (frontend) | `frontend/pages/editors/tiptap.tsx` |
| 10 | Memoize dashboard charts | Small | **Low-Medium** (frontend) | `frontend/pages/dashboard/*.tsx` |
| 5 | Consolidate hash helpers | Trivial | **Low** | `ml/onnx_infer.py`, `quality.py` |
| 7 | Simplify scalar extraction | Trivial | **Low** | Multiple ML files |

Items 1-3 together would yield the most significant CPU reduction with minimal code
change. Item 6 is critical if model training is run frequently.
