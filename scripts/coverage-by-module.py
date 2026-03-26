#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Per-module coverage reporter.

Runs pytest with branch coverage enabled and then parses the XML report to
produce a per-module summary sorted by coverage percentage (ascending so the
worst-covered modules appear first).

Usage::

    python scripts/coverage-by-module.py [--min-coverage N] [--xml-path PATH]

Options:
    --min-coverage N    Fail with exit code 1 if any module is below N %.
                        Defaults to 0 (report-only).
    --xml-path PATH     Path to an already-generated coverage.xml file.
                        When provided, pytest is NOT run again.
    --run-pytest        Re-run pytest before parsing.  Default: run if
                        coverage.xml is absent.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COVERAGE_XML = REPO_ROOT / "coverage.xml"


def _run_pytest() -> int:
    """Run pytest with coverage and return the exit code."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--tb=no",
        "--cov=src",
        "--cov-branch",
        "--cov-report=xml",
        "--cov-report=term-missing",
        str(REPO_ROOT / "tests"),
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode


def _parse_coverage(xml_path: Path) -> list[dict[str, object]]:
    """Return a list of per-file coverage dicts sorted by line-rate ascending."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    rows: list[dict[str, object]] = []
    for pkg in root.iter("package"):
        for cls in pkg.iter("class"):
            filename: str = cls.attrib.get("filename", "?")
            line_rate = float(cls.attrib.get("line-rate", "0"))
            branch_rate = float(cls.attrib.get("branch-rate", "0"))
            lines_valid = int(cls.attrib.get("lines-valid", "0") or "0")
            lines_covered = int(cls.attrib.get("lines-covered", "0") or "0")
            # Normalise path relative to repo root
            try:
                rel = str(Path(filename).relative_to(REPO_ROOT))
            except ValueError:
                rel = filename
            rows.append(
                {
                    "file": rel,
                    "line_pct": round(line_rate * 100, 1),
                    "branch_pct": round(branch_rate * 100, 1),
                    "lines_covered": lines_covered,
                    "lines_valid": lines_valid,
                }
            )

    rows.sort(key=lambda r: r["line_pct"])  # type: ignore[arg-type]
    return rows


def _print_table(rows: list[dict[str, object]]) -> None:
    col_w = max((len(str(r["file"])) for r in rows), default=40)
    col_w = max(col_w, 40)
    header = f"{'File':<{col_w}}  {'Lines %':>8}  {'Branch %':>9}  {'Lines':>12}"
    print(header)
    print("-" * len(header))
    for r in rows:
        cov_str = f"{r['lines_covered']}/{r['lines_valid']}"
        print(
            f"{r['file']:<{col_w}}  {r['line_pct']:>7.1f}%  {r['branch_pct']:>8.1f}%  {cov_str:>12}"
        )
    print("-" * len(header))
    if rows:
        avg_line = sum(r["line_pct"] for r in rows) / len(rows)  # type: ignore[arg-type]
        avg_branch = sum(r["branch_pct"] for r in rows) / len(rows)  # type: ignore[arg-type]
        print(f"{'AVERAGE':<{col_w}}  {avg_line:>7.1f}%  {avg_branch:>8.1f}%")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.0,
        metavar="N",
        help="Fail if any module is below N %% line coverage.",
    )
    parser.add_argument(
        "--xml-path",
        type=Path,
        default=None,
        metavar="PATH",
        help="Use an existing coverage.xml instead of running pytest.",
    )
    parser.add_argument(
        "--run-pytest",
        action="store_true",
        default=False,
        help="Force pytest run even if coverage.xml exists.",
    )
    args = parser.parse_args()

    xml_path: Path = args.xml_path or COVERAGE_XML

    if args.run_pytest or not xml_path.exists():
        rc = _run_pytest()
        if rc != 0:
            print(f"\npytest exited with code {rc}; coverage report may be incomplete.")

    if not xml_path.exists():
        print(f"ERROR: coverage.xml not found at {xml_path}", file=sys.stderr)
        return 1

    rows = _parse_coverage(xml_path)
    if not rows:
        print("No coverage data found.")
        return 0

    _print_table(rows)

    if args.min_coverage > 0:
        below = [r for r in rows if r["line_pct"] < args.min_coverage]  # type: ignore[operator]
        if below:
            print(
                f"\n{len(below)} module(s) below {args.min_coverage}% line coverage:",
                file=sys.stderr,
            )
            for r in below:
                print(f"  {r['file']}: {r['line_pct']}%", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
