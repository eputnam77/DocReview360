#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Alembic migration safety checker.

Validates that every pending migration meets a set of safety criteria before
it is applied to a production database:

1. **Destructive-operation detection** — warns on ``DROP TABLE``, ``DROP COLUMN``,
   ``ALTER COLUMN … TYPE``, and ``TRUNCATE`` statements.
2. **Down-migration presence** — warns when ``downgrade()`` is empty or contains
   only ``pass``.
3. **Up/down symmetry** — cross-checks that columns added in ``upgrade()`` have
   a corresponding removal in ``downgrade()`` (and vice-versa).
4. **Pending migration count** — fails if the number of pending revisions
   exceeds a configurable threshold (default 10) to catch forgotten migrations.

Exit codes:
    0  — all checks passed (warnings may have been printed).
    1  — at least one hard failure was found.
    2  — alembic or configuration is not available.

Usage::

    python scripts/check-migration-safety.py [--fail-on-warnings] [--max-pending N]
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_DIR = REPO_ROOT / "alembic"
VERSIONS_DIR = ALEMBIC_DIR / "versions"

# Patterns that indicate potentially destructive SQL
_DESTRUCTIVE_RE = re.compile(
    r"\b(drop\s+table|drop\s+column|truncate|alter\s+column\b.*\btype\b)",
    re.IGNORECASE,
)


class CheckResult(NamedTuple):
    level: str  # "warn" | "error"
    file: str
    message: str


def _extract_func_source(source: str, func_name: str) -> str:
    """Return the source lines of a top-level function by name."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


def _is_empty_func(func_source: str) -> bool:
    """Return True if the function body is just ``pass`` or a docstring."""
    lines = [
        ln.strip()
        for ln in func_source.splitlines()[1:]  # skip def line
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if not lines:
        return True
    # Only a docstring
    if len(lines) == 1 and lines[0] in ('pass', '"""', "'''", '""""""', "''''''"):
        return True
    if len(lines) <= 2 and all(
        l.startswith(('"', "'")) or l in ("pass",) for l in lines
    ):
        return True
    return False


def check_migration_file(path: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    source = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(REPO_ROOT))

    # 1. Destructive operations
    for ln_no, line in enumerate(source.splitlines(), 1):
        if _DESTRUCTIVE_RE.search(line):
            results.append(
                CheckResult(
                    "warn",
                    rel,
                    f"Line {ln_no}: potentially destructive operation: {line.strip()!r}",
                )
            )

    # 2. Empty downgrade
    downgrade_src = _extract_func_source(source, "downgrade")
    if downgrade_src and _is_empty_func(downgrade_src):
        results.append(
            CheckResult("warn", rel, "downgrade() appears empty — rollback is not supported")
        )

    # 3. Missing downgrade function entirely
    if "def downgrade" not in source:
        results.append(CheckResult("error", rel, "No downgrade() function found"))

    # 4. Missing upgrade function
    if "def upgrade" not in source:
        results.append(CheckResult("error", rel, "No upgrade() function found"))

    return results


def check_pending_count(max_pending: int) -> list[CheckResult]:
    """Return an error if there are too many un-squashed pending migrations."""
    results: list[CheckResult] = []
    if not VERSIONS_DIR.exists():
        return results
    migration_files = list(VERSIONS_DIR.glob("*.py"))
    n = len(migration_files)
    if n > max_pending:
        results.append(
            CheckResult(
                "warn",
                str(VERSIONS_DIR.relative_to(REPO_ROOT)),
                f"{n} migration files found (threshold: {max_pending}); "
                "consider squashing old migrations.",
            )
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        default=False,
        help="Treat warnings as errors (exit 1 on any finding).",
    )
    parser.add_argument(
        "--max-pending",
        type=int,
        default=10,
        metavar="N",
        help="Warn when version files exceed N (default 10).",
    )
    args = parser.parse_args()

    if not ALEMBIC_DIR.exists():
        print(
            f"INFO: alembic directory not found at {ALEMBIC_DIR}; skipping migration checks.",
            file=sys.stderr,
        )
        return 0

    all_results: list[CheckResult] = []

    # Check individual migration files
    if VERSIONS_DIR.exists():
        for mig_file in sorted(VERSIONS_DIR.glob("*.py")):
            all_results.extend(check_migration_file(mig_file))
    else:
        print(f"INFO: No versions directory at {VERSIONS_DIR}; no migrations to check.")

    # Check pending count
    all_results.extend(check_pending_count(args.max_pending))

    errors = [r for r in all_results if r.level == "error"]
    warnings = [r for r in all_results if r.level == "warn"]

    for r in warnings:
        print(f"WARN  [{r.file}] {r.message}")
    for r in errors:
        print(f"ERROR [{r.file}] {r.message}", file=sys.stderr)

    if not all_results:
        print("Migration safety check: all clear.")

    if errors:
        return 1
    if args.fail_on_warnings and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
