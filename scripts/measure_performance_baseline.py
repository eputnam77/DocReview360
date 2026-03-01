"""Measure and record DocReview360 performance baseline metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    from docreview360.performance_baseline import (
        collect_performance_baseline,
        write_performance_baseline_json,
        write_performance_baseline_markdown,
    )

    parser = argparse.ArgumentParser(description="Measure DocReview360 performance baseline.")
    parser.add_argument(
        "--output-json",
        default="dist/perf/performance_baseline.json",
        help="Output JSON path for recorded metrics.",
    )
    parser.add_argument(
        "--output-md",
        default="docs/performance_baseline.md",
        help="Output markdown path for the human-readable baseline report.",
    )
    args = parser.parse_args()

    payload = collect_performance_baseline()
    json_path = write_performance_baseline_json(Path(args.output_json), payload)
    markdown_path = write_performance_baseline_markdown(Path(args.output_md), payload)

    print(f"Wrote performance baseline JSON: {json_path}")
    print(f"Wrote performance baseline markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
