"""Create a signed release tag."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    from docreview360.release_signing import create_signed_git_tag

    parser = argparse.ArgumentParser(description="Create a signed release git tag.")
    parser.add_argument("--tag", required=True, help="Release tag (for example v0.1.0).")
    parser.add_argument("--message", required=True, help="Annotated tag message.")
    parser.add_argument(
        "--key-id",
        default=None,
        help="Optional GPG key id. Uses git default signing key when omitted.",
    )
    args = parser.parse_args()

    output = create_signed_git_tag(args.tag, message=args.message, key_id=args.key_id)
    if output.strip():
        print(output.strip())
    print(f"Signed tag created: {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
