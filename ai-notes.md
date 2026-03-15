# Autoresearch x DocReview360 — Integration Ideas

> Exploratory notes — not committed to implementing any of these yet.
> Reference: <https://github.com/karpathy/autoresearch>

## What Autoresearch Is

Autoresearch (by Andrej Karpathy) is a framework that lets an AI agent
autonomously run ML experiments. The loop is:

1. Agent modifies `train.py` (model architecture, optimizer, hyperparams).
2. Runs training for a fixed 5-minute wall-clock budget.
3. Evaluates via `val_bpb` (validation bits-per-byte).
4. Keeps improvements, discards regressions, repeats.

Humans steer via `program.md` (natural-language instructions). The agent does
the rest overnight.

---

## Why This Could Matter for DocReview360

DocReview360 already ships small ML models (TinyCritic, RoutingCritic,
SignatureAnomalyModel) trained with `docreview360 ml train` and exported to
ONNX. Today, improving these models is a manual process: tweak architecture or
features, retrain, compare metrics, repeat. Autoresearch's core idea —
**automated experiment loops with a fixed time budget** — could accelerate that.

---

## Integration Options

### Option A — Offline Model Improvement Loop (Low coupling, high value)

**Idea:** Adapt the autoresearch loop to optimize DocReview360's own critic
models overnight, without changing the production app at all.

**How it would work:**

- Create a `research/` directory with:
  - `prepare.py` — loads DocReview360 training data (feature vectors + labels)
  - `train.py` — contains the TinyCritic / RoutingCritic architecture + training loop
  - `program.md` — instructions like "improve validation F1 for the quality
    critic while keeping inference < 1ms on CPU"
- Point an AI agent (Claude, etc.) at this setup
- Let it iterate: change hidden dims, activation functions, learning rate
  schedules, feature engineering, regularization, etc.
- After N hours, take the best `train.py`, export to ONNX, and slot it into the
  existing `docreview360 ml package` pipeline

**Pros:**
- Zero changes to production code
- Uses existing `ml/torch_models.py` and `ml/features.py` as starting points
- Time-boxed experiments prevent runaway compute
- Results are just a better `.onnx` file — easy to validate before deploying

**Cons:**
- Requires curating a labeled dataset (approval outcomes, quality scores)
- Single-GPU assumption may limit experiment throughput
- Agent may not understand domain-specific constraints (e.g., feature schema
  compatibility) without careful `program.md` guidance

**Effort:** Low-medium. Mostly scaffolding a `research/` directory and writing
a good `program.md`.

---

### Option B — Continuous Self-Improvement Pipeline (Medium coupling)

**Idea:** Wire autoresearch into the CI/CD or Celery task system so models are
periodically re-evaluated and improved as new review data flows in.

**How it would work:**

- Celery beat task (e.g., weekly) exports recent approval outcomes as training
  data
- Triggers an autoresearch-style loop in a sandboxed environment
- If the new model beats the current one on a held-out validation set, it
  creates a PR or stages the artifact for human review
- Optionally surfaces results in the admin dashboard

**Pros:**
- Models improve automatically as usage patterns change
- Fits the existing Celery + webhook architecture
- Human stays in the loop (PR review or dashboard approval)

**Cons:**
- Needs GPU access in CI/CD or a sidecar service
- More moving parts to maintain
- Data pipeline for labeled examples must be reliable
- Security consideration: sandboxing AI-modified training code

**Effort:** Medium-high. Requires Celery task, data export pipeline, sandboxed
runner, and a comparison harness.

---

### Option C — Feature Engineering Agent (Low coupling, targeted)

**Idea:** Use the autoresearch pattern specifically for discovering better
feature representations in `ml/features.py`, not for architecture search.

**How it would work:**

- Scope `train.py` to only modify the feature extraction pipeline
- Keep model architecture fixed (TinyCritic's 6→16→1 MLP is fine)
- Agent experiments with: new text features, different readability formulas,
  n-gram patterns, structural heuristics, feature normalization, etc.
- Evaluate via the same quality scoring pipeline (`quality.py`)

**Pros:**
- Smaller search space → faster convergence
- Feature changes are more interpretable than architecture changes
- ONNX export stays simple (just input_dim changes)
- Could discover domain-specific signals humans wouldn't think of

**Cons:**
- Feature schema versioning needs care (existing models expect 6 features)
- Some features may require optional dependencies (spaCy, RapidFuzz)

**Effort:** Low. Narrowest scope of all options.

---

### Option D — Approval Routing Optimization (Domain-specific)

**Idea:** Apply autoresearch specifically to the reviewer routing problem: given
a document's features, predict which reviewer will approve fastest / with
highest quality.

**How it would work:**

- Training data: historical (document_features, assigned_reviewer, outcome,
  turnaround_time) tuples
- Agent optimizes the RoutingCritic model and ranking logic
- Metric: approval turnaround time or reviewer agreement rate
- Results feed into `approvals/routing.py`

**Pros:**
- Directly impacts user-visible workflow efficiency
- Clear, measurable business metric
- Existing `ReviewerModel` and `submit_draft_for_approval()` provide the
  integration surface

**Cons:**
- Needs enough historical data to be meaningful
- Routing changes have real workflow consequences — needs careful A/B testing
- Cold-start problem for new teams

**Effort:** Medium. Requires data collection + careful rollout strategy.

---

## Recommendation

If exploring this, **start with Option A** (offline improvement loop). It has
the lowest risk, requires no production code changes, and proves out the concept.
If it yields measurably better models, Option C (feature engineering) is a
natural follow-up. Options B and D are worth revisiting once there's enough
production data and confidence in the approach.

### Quick-Start Sketch for Option A

```
research/
├── program.md          # "Improve quality critic F1. Keep inference <1ms."
├── prepare.py          # Load training data, define eval metrics
├── train.py            # Copy of TinyCritic + training loop from ml/
├── best_train.py       # Auto-saved by agent on improvement
└── logs/               # Experiment history
```

Then point Claude Code (or another agent) at `research/` with autoresearch's
iteration protocol.

---

## Open Questions

- How much labeled training data do we realistically have (or can generate)?
- Is the current 6-feature representation a bottleneck, or is the model
  architecture the limiting factor?
- Would synthetic data (LLM-generated document drafts with known quality
  scores) be useful for bootstrapping?
- Should the time budget be 5 minutes (autoresearch default) or shorter, given
  TinyCritic's small size?
- How do we handle feature schema versioning if the agent discovers a better
  feature set?

---
---

# Recursive Self-Improving Functions — Analysis & Implementation Plan

> Exploratory notes — March 2026. Builds on the autoresearch ideas above.

## What "Recursive Self-Improvement" Means Here

Not AGI-style unbounded recursion. Rather: **closed-loop systems where each
cycle's output becomes the next cycle's input, and the system measurably
improves with each iteration.** The "recursive" part is that improvements
compound — a better quality model produces better training signal for the
routing model, which produces better reviewer assignments, which produce
higher-quality feedback, which makes the quality model even better.

```
                    ┌─────────────────────────┐
                    │   Document Submitted     │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Quality + Compliance    │◄──── Loop A: Score Calibration
                    │  Scoring (ONNX/heuristic)│
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Reviewer Routing        │◄──── Loop B: Routing Optimization
                    │  (ReviewerModel)         │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Human Review + Feedback │
                    │  (FeedbackLedger)        │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │  Outcome Recording       │◄──── Loop C: Threshold Evolution
                    │  (approve/reject/revise) │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────────┐
              ▼              ▼                   ▼
        Loop A feeds    Loop B feeds       Loop C feeds
        back into       back into          back into
        quality model   routing model      compliance rules
```

## Assessment: Yes, This Would Help

DocReview360 already has **most of the raw ingredients** for recursive
self-improvement but lacks the **closed-loop wiring**:

| What exists today | What's missing |
|---|---|
| `quality_assessment()` with hardcoded fallback weights (0.25, 0.12, 0.12, 0.15) | No mechanism to auto-tune these based on outcomes |
| `ReviewerModel.ingest_feedback()` does one-shot preference update + critic retrain | Doesn't run continuously; no validation gate |
| `ReviewTrends` tracks approval scores over time | Data collected but never used to adjust anything |
| `LessonsRepository` collects lessons per project | Lessons stored but not fed back into scoring |
| `FeedbackLedger` captures structured reviewer feedback with tags | Feedback never mined for pattern extraction |
| `estimate_review_effort()` uses fixed coefficients (1.5, 0.7) | No comparison against actual review times |
| `_DOC_TYPE_WEIGHTS` and `_HEURISTIC_WEIGHTS` are static | Could auto-adjust per document type |
| `_LOWER_THAN_RULES` / `_GREATER_THAN_RULES` in compliance classifier are hardcoded | No appeal/override tracking to evolve thresholds |

---

## Six Concrete Self-Improvement Loops

### Loop A — Quality Score Calibration (Highest Impact)

**Current state:** `quality.py:130-152` uses hardcoded fallback weights.
`quality.py:155-172` runs ONNX inference with static model weights.

**Recursive loop:**
1. Quality model scores document → produces `QualityAssessment`
2. Reviewer provides feedback (accept/reject/suggest changes via FeedbackLedger)
3. System records `(predicted_score, actual_outcome)` pairs
4. Periodically: compute calibration error (predicted vs actual approval rate)
5. Adjust fallback weights or retrain ONNX model to minimize error
6. New model produces better predictions → better feedback signal → repeat

**Where it touches code:**
- `quality.py` — `_fallback_quality_assessment()` weights become tunable parameters
- `feedback_ledger.py` — query feedback dispositions as training signal
- New: `self_improve/calibration.py` — calibration loop logic

**Implementation sketch:**
```python
# self_improve/calibration.py
@dataclass
class CalibrationSnapshot:
    """One cycle's measurements."""
    cycle: int
    timestamp: datetime
    predicted_scores: list[float]
    actual_outcomes: list[bool]  # approved = True
    mae: float  # mean absolute error
    weights_before: dict[str, float]
    weights_after: dict[str, float]

def calibration_cycle(
    lookback_days: int = 30,
    min_samples: int = 50,
) -> CalibrationSnapshot | None:
    """Run one calibration cycle. Returns None if insufficient data."""
    # 1. Pull recent (document_id, predicted_score, actual_outcome) pairs
    pairs = _collect_prediction_outcome_pairs(lookback_days)
    if len(pairs) < min_samples:
        return None  # not enough data to learn from

    # 2. Measure current calibration error
    mae_before = mean_absolute_error(
        [p.predicted for p in pairs],
        [float(p.approved) for p in pairs],
    )

    # 3. Fit adjusted weights via scipy.optimize.minimize
    #    Objective: minimize MAE on the collected pairs
    #    Constraints: weights stay within [0.01, 2.0] to prevent collapse
    new_weights = _optimize_weights(pairs)

    # 4. Validate on held-out 20% split
    mae_after = _validate_weights(new_weights, pairs)

    # 5. Only apply if strictly better (with margin)
    if mae_after < mae_before * 0.95:  # 5% improvement gate
        _apply_weights(new_weights)

    return CalibrationSnapshot(...)
```

**Estimated effort:** Low-medium. No new dependencies. Mostly plumbing
feedback outcomes to quality scoring.

---

### Loop B — Reviewer Routing Recursive Improvement

**Current state:** `reviewer_model.py:294-302` `ingest_feedback()` does
one-shot preference update + critic retrain. But it's called manually and
doesn't validate whether the update actually improved routing.

**Recursive loop:**
1. Route document to reviewer via `recommend()` → ranked list
2. Observe: did the top-ranked reviewer accept or request changes?
3. Compute routing accuracy: `correct_routes / total_routes` over window
4. If accuracy declining: retrain routing critic on recent outcomes
5. Validate retrained model on held-out data before deploying
6. Better routing → reviewers get docs matching their expertise → faster
   turnaround → cleaner training signal → even better routing

**Where it touches code:**
- `reviewer_model.py` — `ingest_feedback()` becomes part of a periodic loop
- `review_analytics.py` — `ReviewTrends` data feeds routing evaluation
- New: `self_improve/routing.py` — routing accuracy tracker + retrain trigger

**Key constraint:** Routing changes have real workflow consequences. Must A/B
test before full rollout (e.g., route 80% with current model, 20% with
candidate, compare acceptance rates).

---

### Loop C — Compliance Threshold Evolution

**Current state:** `compliance_classifier.py:63-71` hardcodes rule thresholds
(readability < 0.45, structure < 0.55, etc.).

**Recursive loop:**
1. Compliance classifier flags documents with rule violations
2. Reviewers can appeal/override (via feedback ledger: "non_concurrence" type)
3. Track false positive rate per rule: overrides ÷ total flags
4. Rules with high false-positive rates: relax threshold slightly
5. Rules with high miss rate (docs pass but later fail audit): tighten
6. Tighter/better thresholds → fewer false flags → more reviewer trust →
   better override signal → even better thresholds

**Implementation:** Lightweight — just needs an override counter per rule and
a periodic threshold adjustment with bounds.

```python
# Threshold adjustment with guardrails
THRESHOLD_BOUNDS = {
    "readability": (0.30, 0.65),      # never go below 0.30 or above 0.65
    "structure": (0.35, 0.70),
    "metadata_completeness": (0.50, 0.90),
    "style": (0.30, 0.65),
    "compliance_risk": (0.40, 0.80),
}
ADJUSTMENT_STEP = 0.02  # max 2% shift per cycle
```

---

### Loop D — Feedback Pattern Mining → Checker Rule Generation

**Current state:** `document_checker.py` uses static heuristic rules.
`feedback_ledger.py` captures structured feedback but nobody mines it.

**Recursive loop:**
1. Reviewers leave feedback (suggestions, non-concurrences) with text
2. Periodically: cluster feedback text by semantic similarity
3. Extract recurring patterns (e.g., "missing date in header" appears 40 times)
4. Generate candidate checker rules from frequent patterns
5. Validate candidate rules against historical documents (precision/recall)
6. High-quality rules get promoted to document_checker.py
7. Fewer repeated feedback items → reviewers flag new patterns → mine those

**This is the most "recursive" loop** — the system literally writes its own
rules based on aggregated human intelligence, then those rules surface issues
earlier, freeing reviewers to find subtler problems, which become the next
generation of rules.

**Implementation complexity:** Medium-high. Requires text clustering (could use
existing feature extraction + cosine similarity, no LLM needed for v1).

---

### Loop E — Effort Estimation Self-Correction

**Current state:** `review_analytics.py:17-38` `estimate_review_effort()` uses
hardcoded coefficients: `length * 1.5 + repeated * 0.7 + ...`

**Recursive loop:**
1. Estimate review effort for incoming document
2. Record actual review duration (time from assignment to approval)
3. Compare predicted vs actual across recent window
4. Fit new coefficients via least-squares regression
5. Better estimates → better workload balancing → more consistent review
   times → cleaner training signal → better estimates

**This is the simplest loop to implement** — it's literally linear regression
on 6 features with known labels (actual duration).

```python
def recalibrate_effort_weights(
    predictions: list[float],
    actuals: list[float],
    features_matrix: np.ndarray,
) -> np.ndarray:
    """Least-squares fit for effort estimation coefficients."""
    # np.linalg.lstsq — no new dependencies needed
    weights, _, _, _ = np.linalg.lstsq(features_matrix, actuals, rcond=None)
    return weights
```

---

### Loop F — Feature Weight Auto-Tuning per Document Type

**Current state:** `quality.py:91-95` has static `_DOC_TYPE_WEIGHTS` for
"policy_memo" and "rulemaking".

**Recursive loop:**
1. Score documents using current per-type weights
2. Track prediction accuracy per document type
3. Types with low accuracy: adjust weights using gradient descent on outcomes
4. Types with high accuracy: freeze weights (don't over-fit)
5. New document types emerge → start with default weights → loop begins

---

## Implementation Architecture

### New Module: `src/docreview360/self_improve/`

```
src/docreview360/self_improve/
├── __init__.py              # Shared types, SelfImproveCycle base class
├── calibration.py           # Loop A: quality score calibration
├── routing.py               # Loop B: reviewer routing optimization
├── thresholds.py            # Loop C: compliance threshold evolution
├── rule_mining.py           # Loop D: feedback → checker rules
├── effort.py                # Loop E: effort estimation recalibration
├── feature_weights.py       # Loop F: per-type weight tuning
├── snapshots.py             # Versioned parameter snapshots for rollback
└── scheduler.py             # Celery beat integration
```

### Core Abstractions

```python
@dataclass
class ImprovementCycle:
    """Base for all self-improvement cycles."""
    cycle_id: str
    started_at: datetime
    completed_at: datetime | None
    metric_before: float
    metric_after: float | None
    applied: bool  # False if improvement gate not met
    rollback_snapshot: str  # path to parameter snapshot

class SelfImproveLoop(ABC):
    """Protocol for recursive improvement loops."""

    @abstractmethod
    def measure(self) -> float:
        """Compute current performance metric."""

    @abstractmethod
    def propose(self) -> dict[str, Any]:
        """Propose parameter adjustments."""

    @abstractmethod
    def validate(self, proposed: dict[str, Any]) -> float:
        """Validate proposed changes, return new metric."""

    @abstractmethod
    def apply(self, proposed: dict[str, Any]) -> None:
        """Apply validated changes."""

    def run_cycle(self) -> ImprovementCycle:
        """Execute one measure→propose→validate→apply cycle."""
        before = self.measure()
        proposed = self.propose()
        after = self.validate(proposed)
        snapshot = self._save_snapshot()
        applied = after > before * (1 + self.improvement_gate)
        if applied:
            self.apply(proposed)
        return ImprovementCycle(...)
```

### Safety Guardrails (Critical)

Recursive self-improvement without guardrails is dangerous. Every loop must
enforce:

1. **Improvement gate:** Changes only apply if metric improves by >N%
   (default 5%). Prevents noise-driven drift.
2. **Bounded parameters:** Every tunable value has hard min/max bounds.
   Thresholds can't collapse to 0 or explode to 1.
3. **Rollback snapshots:** Every cycle saves a snapshot. Any cycle can be
   reverted with `docreview360 self-improve rollback <cycle-id>`.
4. **Human approval gate:** In production, parameter changes are staged as
   proposals visible in the admin dashboard. An admin must approve before
   they take effect. (In dev, auto-apply is allowed.)
5. **Rate limiting:** Max one cycle per loop per 24h in production. Prevents
   oscillation from rapid parameter swings.
6. **Convergence detection:** If the last 5 cycles show <1% total improvement,
   the loop suspends itself and alerts an admin. Prevents wasted compute on
   diminishing returns.
7. **Audit trail:** Every cycle is logged to the existing audit system with
   full before/after parameter diffs.

### Celery Integration

```python
# scheduler.py
from celery import shared_task
from celery.schedules import crontab

SELF_IMPROVE_SCHEDULE = {
    "calibrate-quality-weekly": {
        "task": "docreview360.self_improve.calibration.run_cycle",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
    "recalibrate-effort-weekly": {
        "task": "docreview360.self_improve.effort.run_cycle",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
    },
    "evolve-thresholds-monthly": {
        "task": "docreview360.self_improve.thresholds.run_cycle",
        "schedule": crontab(hour=4, minute=0, day_of_month="1"),
    },
    "mine-rules-monthly": {
        "task": "docreview360.self_improve.rule_mining.run_cycle",
        "schedule": crontab(hour=5, minute=0, day_of_month="15"),
    },
}
```

### CLI Commands

```bash
# Run a specific improvement cycle manually
docreview360 self-improve run calibration
docreview360 self-improve run effort --dry-run

# View cycle history
docreview360 self-improve history --loop calibration --last 10

# Rollback a specific cycle
docreview360 self-improve rollback <cycle-id>

# View current tunable parameters vs defaults
docreview360 self-improve params --diff
```

---

## Compound Improvement (The Recursive Part)

The six loops aren't independent — they form a **reinforcing cycle**:

```
Better quality scores (A)
    → Better reviewer routing (B)
        → Faster, more accurate reviews
            → Cleaner feedback signal
                → Better threshold evolution (C)
                    → Fewer false positives
                        → More reviewer trust
                            → Higher-quality feedback
                                → Better quality scores (A) ← RECURSIVE
```

This is the key insight: **each loop's output improves the input quality for
other loops.** The compound effect means the system improves faster than any
single loop would on its own.

Potential risk: **feedback loops can amplify errors too.** If the quality model
develops a blind spot, the routing model will systematically send those
documents to the wrong reviewers, who will provide lower-quality feedback,
which reinforces the blind spot. This is why the safety guardrails above
(bounded parameters, human approval gates, rollback) are non-negotiable.

---

## Recommended Implementation Order

| Phase | Loop | Why first | Effort | Dependencies |
|-------|------|-----------|--------|-------------|
| 1 | **E: Effort Estimation** | Simplest (linear regression). Proves the pattern. | Low | numpy (already present) |
| 2 | **A: Quality Calibration** | Highest impact. Feeds all other loops. | Low-Med | feedback_ledger queries |
| 3 | **C: Threshold Evolution** | Quick win. Static thresholds are a known pain point. | Low | Override tracking in feedback_ledger |
| 4 | **B: Routing Optimization** | Requires enough routing history. | Medium | ReviewerModel persistence |
| 5 | **F: Feature Weights** | Needs per-type outcome data. | Medium | Document type tracking |
| 6 | **D: Rule Mining** | Most complex. Requires text clustering. | Med-High | Feedback volume + clustering |

**Phase 1 target:** Loops E and A working in dev with CLI commands.
No Celery dependency, no production deployment.

**Phase 2 target:** Loops C and B added. Celery scheduler for automated
cycles. Admin dashboard panel showing cycle history + pending proposals.

**Phase 3 target:** Loops F and D. Full compound improvement active.
A/B testing framework for routing changes.

---

## Relationship to Autoresearch (Section Above)

Autoresearch and recursive self-improvement are complementary:

- **Autoresearch** optimizes model **architecture** (hidden dims, activations,
  learning rate) by running AI-guided experiments offline. It produces a better
  `.onnx` file.
- **Recursive self-improvement** optimizes model **parameters and thresholds**
  continuously in production based on real usage data. It tunes the knobs on
  the existing architecture.

Ideally: autoresearch finds the best architecture quarterly, then recursive
self-improvement keeps it calibrated daily/weekly.

---

## Open Questions

- What minimum data volume per loop before the first cycle is meaningful?
  (Rough estimates: Loop E needs 100+ reviewed documents with timestamps,
  Loop A needs 50+ with feedback dispositions.)
- Should the `SelfImproveLoop` base class be an ABC or a Protocol?
  Protocol is more Pythonic but ABC enforces method signatures at class
  definition time.
- How do we handle multi-tenant deployments where different organizations
  have different baselines? Per-org parameter namespacing?
- Should compound improvement cycles (A→B→C in sequence) be orchestrated
  as a single Celery chain, or independent tasks that check prerequisites?
- What's the right dashboard UX for "the system wants to change these
  parameters — approve or reject"?
