"""Run a disaster recovery backup/restore simulation for release readiness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def main() -> int:
    from docreview360.disaster_recovery import run_disaster_recovery_simulation

    parser = argparse.ArgumentParser(description="Run DocReview360 disaster recovery simulation.")
    parser.add_argument(
        "--backup-path",
        default=".tmp/dr-simulation.json.gz",
        help="Backup path used for the simulation.",
    )
    args = parser.parse_args()

    result = run_disaster_recovery_simulation(Path(args.backup_path))
    print("Disaster recovery simulation passed.")
    print(f"Backup path: {result.backup_path}")
    print(f"Project restored: {result.project_id}")
    print(f"Document restored: {result.document_id}")
    print(f"Version count restored: {result.restored_version_count}")
    print(f"Log entries restored: {result.restored_log_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
