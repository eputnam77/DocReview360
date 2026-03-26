#!/usr/bin/env bash
# check_release.sh — Pre-release quality gate runner.
# Prints PASS or FAIL for each step; exits 1 if any step fails.
set -euo pipefail

PASS=0
FAIL=0

run_step() {
    local label="$1"
    shift
    echo ""
    echo "==> $label"
    if "$@"; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label"
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Step 1: pytest with branch coverage gate (90%)
# ---------------------------------------------------------------------------
run_step "pytest coverage (>=90%)" \
    pytest -q --cov=src --cov-branch --cov-report=term --cov-fail-under=90

# ---------------------------------------------------------------------------
# Step 2: Bandit security scan (high-severity issues only, skip B101)
# ---------------------------------------------------------------------------
run_step "bandit security scan" \
    bandit -r src -lll --skip B101

# ---------------------------------------------------------------------------
# Step 3: mkdocs config parse check (import + config load, no strict build)
# ---------------------------------------------------------------------------
mkdocs_check() {
    python - <<'PYEOF'
import sys
try:
    from mkdocs.config import load_config
    load_config("mkdocs.yml")
    print("mkdocs.yml parsed successfully.")
except ImportError:
    print("mkdocs not installed — skipping parse check.")
    sys.exit(0)
except Exception as e:
    print(f"mkdocs config error: {e}")
    sys.exit(1)
PYEOF
}
run_step "mkdocs config parse" mkdocs_check

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "-----------------------------------"
echo "Results: ${PASS} passed, ${FAIL} failed."
echo "-----------------------------------"

if [ "$FAIL" -gt 0 ]; then
    echo "OVERALL: FAIL"
    exit 1
else
    echo "OVERALL: PASS"
    exit 0
fi
