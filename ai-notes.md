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
