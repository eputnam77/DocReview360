"""Verify a signed release tag."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    from docreview360.release_signing import verify_git_tag_signature

    parser = argparse.ArgumentParser(description="Verify a signed release git tag.")
    parser.add_argument("--tag", required=True, help="Release tag (for example v0.1.0).")
    args = parser.parse_args()

    output = verify_git_tag_signature(args.tag)
    if output.strip():
        print(output.strip())
    print(f"Tag signature verified: {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
