"""Generate DocReview360 release notes with optional container digests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    from docreview360.release_notes import generate_release_notes, read_project_version

    parser = argparse.ArgumentParser(
        description="Generate release notes and include published container digests."
    )
    parser.add_argument(
        "--output",
        default="dist/release/RELEASE_NOTES.md",
        help="Output path for generated release notes markdown.",
    )
    parser.add_argument(
        "--version",
        default="",
        help="Release version. Defaults to [project].version in pyproject.toml.",
    )
    parser.add_argument(
        "--image-digest",
        action="append",
        default=[],
        help="Container digest in '<image>@sha256:<digest>' format. Repeat for multiple images.",
    )
    args = parser.parse_args()

    version = args.version.strip() or read_project_version(REPO_ROOT / "pyproject.toml")
    output = Path(args.output)
    generated = generate_release_notes(
        output,
        version=version,
        container_digests=args.image_digest,
    )
    print(f"Generated release notes: {generated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
