"""Generate a CycloneDX SBOM for DocReview360 release artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    from docreview360.sbom import generate_cyclonedx_sbom

    parser = argparse.ArgumentParser(description="Generate CycloneDX SBOM JSON.")
    parser.add_argument(
        "--output",
        default="dist/sbom/docreview360.cdx.json",
        help="Output file path for CycloneDX JSON SBOM.",
    )
    args = parser.parse_args()

    output = Path(args.output)
    path = generate_cyclonedx_sbom(output)
    print(f"Generated CycloneDX SBOM: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
