#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Performance regression loop.

Reruns scripts/measure_performance_baseline.py, compares results to
docs/performance_baseline.md thresholds, and reports regressions.
Always exits 0 (informational).

Usage:
    python scripts/performance-regression-check.py
    python scripts/performance-regression-check.py --threshold 0.5
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_SCRIPT = REPO_ROOT / "scripts" / "measure_performance_baseline.py"
BASELINE_DOC = REPO_ROOT / "docs" / "performance_baseline.md"

findings: list[dict[str, str]] = []


def note(category: str, severity: str, message: str) -> None:
    findings.append({"category": category, "severity": severity, "message": message})
    indicator = "!" if severity in ("CRITICAL", "HIGH") else "~"
    print(f"  [{indicator}] [{category}] {severity}: {message}")


def ok(category: str, message: str) -> None:
    print(f"  [+] [{category}] ok: {message}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def check_baseline_doc() -> dict[str, float]:
    """Parse documented thresholds from performance_baseline.md."""
    section("Documented Performance Thresholds")

    if not BASELINE_DOC.exists():
        note("Baseline", "MEDIUM", "docs/performance_baseline.md not found — no thresholds to compare")
        return {}

    text = BASELINE_DOC.read_text(encoding="utf-8")
    ok("Baseline", f"performance_baseline.md found ({len(text)} chars)")

    # Extract metric: `value` patterns
    thresholds: dict[str, float] = {}
    for m in re.finditer(r"-\s+(.+?):\s+`([\d.]+)s`", text):
        label = m.group(1).strip().lower()
        value = float(m.group(2))
        thresholds[label] = value
        ok("Baseline", f"  threshold: {label} = {value}s")

    if not thresholds:
        note("Baseline", "LOW", "No threshold values found in performance_baseline.md")

    return thresholds


def run_baseline_measurement(threshold_pct: float) -> dict[str, float] | None:
    """Run measure_performance_baseline.py and return new metrics from JSON."""
    section("Running Performance Measurement")

    if not BASELINE_SCRIPT.exists():
        note("Measurement", "HIGH", "scripts/measure_performance_baseline.py not found")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        output_json = str(Path(tmpdir) / "perf.json")
        try:
            result = subprocess.run(
                [sys.executable, str(BASELINE_SCRIPT), "--output-json", output_json],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            note("Measurement", "HIGH", "Performance measurement timed out after 120s")
            return None

        if result.returncode != 0:
            note(
                "Measurement",
                "MEDIUM",
                f"measure_performance_baseline.py exited {result.returncode} — using documented values only",
            )
            return None

        json_path = Path(output_json)
        if not json_path.exists():
            note("Measurement", "MEDIUM", "No JSON output produced by measurement script")
            return None

        try:
            data = json.loads(json_path.read_text())
            ok("Measurement", f"New metrics collected: {len(data)} entries")
            return {str(k).lower(): float(v) for k, v in data.items() if isinstance(v, (int, float))}
        except (json.JSONDecodeError, ValueError) as exc:
            note("Measurement", "MEDIUM", f"Could not parse metrics JSON: {exc}")
            return None


def compare_metrics(
    baseline: dict[str, float],
    current: dict[str, float],
    threshold_pct: float,
) -> None:
    section(f"Regression Comparison (threshold: +{threshold_pct * 100:.0f}%)")

    if not baseline or not current:
        note("Comparison", "LOW", "Cannot compare — missing baseline or current metrics")
        return

    regressions = 0
    for key, base_val in baseline.items():
        # find matching current metric (fuzzy key match)
        cur_val = current.get(key)
        if cur_val is None:
            for cur_key, cur_v in current.items():
                if key in cur_key or cur_key in key:
                    cur_val = cur_v
                    break

        if cur_val is None:
            note("Comparison", "LOW", f"No current measurement for '{key}' — skipping")
            continue

        change = (cur_val - base_val) / base_val if base_val > 0 else 0
        if change > threshold_pct:
            note(
                "Regression",
                "HIGH",
                f"{key}: {base_val:.4f}s → {cur_val:.4f}s "
                f"(+{change * 100:.1f}% — REGRESSION)",
            )
            regressions += 1
        else:
            ok("Comparison", f"{key}: {base_val:.4f}s → {cur_val:.4f}s ({change * 100:+.1f}%)")

    if regressions == 0:
        ok("Comparison", f"No regressions detected (all within +{threshold_pct * 100:.0f}%)")


def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  PERFORMANCE REGRESSION SUMMARY")
    print("=" * 60)

    if not findings:
        print("  All performance metrics within acceptable thresholds.")
        print("=" * 60)
        return

    by_severity: dict[str, list[dict[str, str]]] = {}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        print(f"\n  [{sev}] — {len(items)} finding(s):")
        for item in items:
            print(f"    [{item['category']}] {item['message'][:100]}")

    print(f"\n  Total: {len(findings)} issue(s) across {len(by_severity)} severity level(s).")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="DocReview360 performance regression check.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Regression threshold as fraction (default: 0.5 = 50%% slower)",
    )
    args = parser.parse_args()

    print("DocReview360 Performance Regression Check")
    print(f"Repo root: {REPO_ROOT}")
    print(f"Threshold: +{args.threshold * 100:.0f}% regression triggers a finding")

    baseline = check_baseline_doc()
    current = run_baseline_measurement(args.threshold)

    if current is not None:
        compare_metrics(baseline, current, args.threshold)
    else:
        section("Skipping Comparison")
        print("  skip : could not collect current metrics — review findings above")

    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
