#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# headless-loop.sh — Raspberry Pi-friendly headless automation runner.
#
# A minimal shell wrapper for running autonomous maintenance commands
# in a resource-constrained, headless environment (Raspberry Pi, VMs, CI).
#
# Features:
#   - Lockfile: only one loop instance at a time
#   - Append-only log: never truncates, each run adds a header
#   - No cron/systemd required: run manually or via simple shell scheduler
#   - Configurable via environment variables
#   - Exits gracefully with meaningful exit codes
#
# Watchdog: stops the loop on budget exhaustion or repeated failures.
#   - HEADLESS_MAX_FAILURES: stop after N consecutive failures (default: 3)
#   - HEADLESS_BUDGET_SECS:  stop after N wall-clock seconds total (default: 3600)
#
# Environment variables:
#   HEADLESS_COMMAND      — command to run (default: 'python scripts/check-docs-drift.py')
#   HEADLESS_LOG_FILE     — log file path (default: artifacts/automation/headless.log)
#   HEADLESS_MAX_RUNS     — max run count per invocation (default: 1)
#   HEADLESS_LOCKFILE     — lockfile path (default: .headless.lock)
#   HEADLESS_MAX_FAILURES — watchdog: stop after N consecutive failures (default: 3)
#   HEADLESS_BUDGET_SECS  — watchdog: stop after N wall-clock seconds (default: 3600)
#
# Usage:
#   ./scripts/headless-loop.sh
#   HEADLESS_COMMAND='pytest -q --tb=short -x' ./scripts/headless-loop.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Configuration ─────────────────────────────────────────────────────────────
HEADLESS_COMMAND="${HEADLESS_COMMAND:-python scripts/check-docs-drift.py}"
HEADLESS_LOG_FILE="${HEADLESS_LOG_FILE:-${REPO_ROOT}/artifacts/automation/headless.log}"
HEADLESS_MAX_RUNS="${HEADLESS_MAX_RUNS:-1}"
HEADLESS_LOCKFILE="${HEADLESS_LOCKFILE:-${REPO_ROOT}/.headless.lock}"
HEADLESS_MAX_FAILURES="${HEADLESS_MAX_FAILURES:-3}"
HEADLESS_BUDGET_SECS="${HEADLESS_BUDGET_SECS:-3600}"

# ── Lockfile ──────────────────────────────────────────────────────────────────
if [ -e "${HEADLESS_LOCKFILE}" ]; then
    echo "ERROR: Another headless loop is running (lockfile: ${HEADLESS_LOCKFILE})." >&2
    echo "       If the previous run crashed, remove: ${HEADLESS_LOCKFILE}" >&2
    exit 2
fi
echo "$$" > "${HEADLESS_LOCKFILE}"
trap 'rm -f "${HEADLESS_LOCKFILE}"' EXIT INT TERM

# ── Log directory ─────────────────────────────────────────────────────────────
mkdir -p "$(dirname "${HEADLESS_LOG_FILE}")"

# Append-only log header
{
    echo ""
    echo "========================================"
    echo "headless-loop.sh run at $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "PID: $$  MAX_RUNS: ${HEADLESS_MAX_RUNS}"
    echo "COMMAND: ${HEADLESS_COMMAND}"
    echo "========================================"
} >> "${HEADLESS_LOG_FILE}"

# ── Main loop + watchdog ──────────────────────────────────────────────────────
RUNS=0
EXIT_CODE=0
CONSECUTIVE_FAILURES=0
LOOP_START="$(date +%s)"

while [ "${RUNS}" -lt "${HEADLESS_MAX_RUNS}" ]; do
    # Watchdog: budget check
    NOW="$(date +%s)"
    ELAPSED=$((NOW - LOOP_START))
    if [ "${ELAPSED}" -ge "${HEADLESS_BUDGET_SECS}" ]; then
        echo "  WATCHDOG: budget exhausted (${ELAPSED}s >= ${HEADLESS_BUDGET_SECS}s) — stopping" | tee -a "${HEADLESS_LOG_FILE}"
        EXIT_CODE=3
        break
    fi

    RUNS=$((RUNS + 1))
    echo "  [run ${RUNS}/${HEADLESS_MAX_RUNS}] starting..." | tee -a "${HEADLESS_LOG_FILE}"

    # Run the command, tee output to the append-only log
    if bash -c "${HEADLESS_COMMAND}" 2>&1 | tee -a "${HEADLESS_LOG_FILE}"; then
        echo "  [run ${RUNS}] EXIT 0 — ok" | tee -a "${HEADLESS_LOG_FILE}"
        CONSECUTIVE_FAILURES=0
    else
        EXIT_CODE=$?
        CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
        echo "  [run ${RUNS}] EXIT ${EXIT_CODE} — failure (${CONSECUTIVE_FAILURES} consecutive)" | tee -a "${HEADLESS_LOG_FILE}"
        # Watchdog: stop after repeated failures
        if [ "${CONSECUTIVE_FAILURES}" -ge "${HEADLESS_MAX_FAILURES}" ]; then
            echo "  WATCHDOG: ${CONSECUTIVE_FAILURES} consecutive failures — stopping" | tee -a "${HEADLESS_LOG_FILE}"
            EXIT_CODE=4
            break
        fi
    fi
done

echo "headless-loop finished: ${RUNS} run(s), exit ${EXIT_CODE}" | tee -a "${HEADLESS_LOG_FILE}"
exit "${EXIT_CODE}"
