#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit-log integrity loop.

Verifies append-only behavior, hash-chain validation, retention settings,
and backup/restore steps after risky backend changes.
Always exits 0 (informational).

Usage:
    python scripts/audit-log-integrity-check.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "docreview360"

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


# ---------------------------------------------------------------------------
# 1. Log package source checks
# ---------------------------------------------------------------------------

def check_log_package_structure() -> None:
    section("Audit Log Package Structure")

    logs_dir = SRC / "logs"
    if not logs_dir.is_dir():
        note("Structure", "HIGH", "src/docreview360/logs/ package not found")
        return

    ok("Structure", "logs/ package directory present")

    required_modules = ["__init__.py", "_db.py", "_dispatch.py", "_query.py"]
    for mod in required_modules:
        if (logs_dir / mod).exists():
            ok("Structure", f"logs/{mod} present")
        else:
            note("Structure", "MEDIUM", f"logs/{mod} missing")

    # Check __init__.py exports
    init = logs_dir / "__init__.py"
    if init.exists():
        text = init.read_text(encoding="utf-8")
        for export in ["log_event", "query_logs", "verify_audit_log_chain"]:
            if export in text:
                ok("Structure", f"{export} exported from logs package")
            else:
                note("Structure", "MEDIUM", f"{export} not exported from logs/__init__.py")


# ---------------------------------------------------------------------------
# 2. Hash-chain verification
# ---------------------------------------------------------------------------

def check_hash_chain() -> None:
    section("Hash-Chain Verification")

    query_path = SRC / "logs" / "_query.py"
    if not query_path.exists():
        note("HashChain", "HIGH", "logs/_query.py not found — cannot verify hash-chain code")
        return

    text = query_path.read_text(encoding="utf-8")

    if "verify_audit_log_chain" in text:
        ok("HashChain", "verify_audit_log_chain function present")
    else:
        note("HashChain", "HIGH", "verify_audit_log_chain not found in _query.py")

    if "sha" in text.lower() or "hash" in text.lower() or "hmac" in text.lower():
        ok("HashChain", "Hash/HMAC computation detected in _query.py")
    else:
        note("HashChain", "HIGH", "No SHA/hash/HMAC computation detected in _query.py")

    if "prev_hash" in text or "previous_hash" in text or "chain" in text.lower():
        ok("HashChain", "Chain link (prev_hash / chain) logic detected")
    else:
        note("HashChain", "MEDIUM", "No chain-link pattern (prev_hash) detected")

    # Try importing and running the chain verifier
    try:
        sys.path.insert(0, str(REPO_ROOT / "src"))
        os.environ.setdefault("DOCREVIEW360_ENV", "dev")
        from docreview360.logs import log_event, verify_audit_log_chain  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["DOCREVIEW360_DB_PATH"] = str(Path(tmpdir) / "test.db")
            log_event("integrity_check_test", "system", details={"check": "audit-log-integrity"})
            result = verify_audit_log_chain()
            if isinstance(result, tuple):
                valid, broken = result
            else:
                valid = bool(result)
                broken = []

            if valid:
                ok("HashChain", "verify_audit_log_chain() returned valid=True on fresh log")
            else:
                note("HashChain", "MEDIUM", f"verify_audit_log_chain() returned invalid — broken: {broken}")
    except ImportError as exc:
        note("HashChain", "LOW", f"Cannot import docreview360.logs in this env: {exc}")
    except Exception as exc:  # noqa: BLE001
        note("HashChain", "MEDIUM", f"verify_audit_log_chain() raised: {exc!r}")


# ---------------------------------------------------------------------------
# 3. Append-only behavior
# ---------------------------------------------------------------------------

def check_append_only() -> None:
    section("Append-only Log Behavior")

    dispatch_path = SRC / "logs" / "_dispatch.py"
    db_path = SRC / "logs" / "_db.py"

    for path in (dispatch_path, db_path):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")

        if "DELETE" in text.upper() and "audit" in text.lower():
            note("AppendOnly", "MEDIUM", f"{path.name}: DELETE on audit log table found — verify this is retention-only")
        else:
            ok("AppendOnly", f"{path.name}: no unrestricted DELETE on audit log")

        if "UPDATE" in text.upper() and "audit" in text.lower():
            note("AppendOnly", "HIGH", f"{path.name}: UPDATE on audit log table found — logs must be immutable")
        else:
            ok("AppendOnly", f"{path.name}: no UPDATE on audit log (immutable)")

    # Check retention code
    retention = SRC / "data_retention.py"
    if retention.exists():
        ret_text = retention.read_text(encoding="utf-8")
        if "RETAIN" in ret_text and ("audit" in ret_text.lower() or "log" in ret_text.lower()):
            ok("AppendOnly", "data_retention.py has audit log retention config")
        if "run_retention_pass" in ret_text:
            ok("AppendOnly", "run_retention_pass() function present")
    else:
        note("AppendOnly", "MEDIUM", "data_retention.py not found — no automated retention")


# ---------------------------------------------------------------------------
# 4. Retention settings
# ---------------------------------------------------------------------------

def check_retention_settings() -> None:
    section("Retention Settings")

    retention = SRC / "data_retention.py"
    if not retention.exists():
        note("Retention", "MEDIUM", "data_retention.py not found")
        return

    text = retention.read_text(encoding="utf-8")

    retain_env_vars = [
        "DOCREVIEW360_RETAIN_AUDIT_DAYS",
        "DOCREVIEW360_RETAIN_NOTIFICATION_DAYS",
        "DOCREVIEW360_RETAIN_SESSION_DAYS",
    ]
    for var in retain_env_vars:
        if var in text:
            ok("Retention", f"{var} configurable via env")
        else:
            note("Retention", "LOW", f"{var} not found in data_retention.py")

    # Check for reasonable defaults
    import re
    defaults = re.findall(r'RETAIN_\w+_DAYS.*?(\d+)', text)
    for d in defaults[:5]:
        days = int(d)
        if days >= 30:
            ok("Retention", f"Retention default of {days} days (>=30 — compliant)")
        else:
            note("Retention", "MEDIUM", f"Retention default of {days} days may be too short for compliance")


# ---------------------------------------------------------------------------
# 5. Backup / restore scripts
# ---------------------------------------------------------------------------

def check_backup_restore() -> None:
    section("Backup / Restore Scripts")

    backup_script = REPO_ROOT / "scripts" / "db_backup.sh"
    if backup_script.exists():
        text = backup_script.read_text(encoding="utf-8")
        ok("Backup", "scripts/db_backup.sh present")

        if "openssl" in text or "encrypt" in text.lower():
            ok("Backup", "Encrypted backup (openssl) detected")
        else:
            note("Backup", "MEDIUM", "No encryption in db_backup.sh — backups may be in plaintext")

        if "aes" in text.lower() or "AES" in text:
            ok("Backup", "AES encryption algorithm detected in backup script")

        if "trap" in text or "cleanup" in text.lower():
            ok("Backup", "Cleanup/trap handler in backup script")
    else:
        note("Backup", "MEDIUM", "scripts/db_backup.sh not found — no automated backup")

    # Check docs for restore steps
    dr_doc = REPO_ROOT / "docs" / "disaster_recovery.md"
    if dr_doc.exists():
        dr_text = dr_doc.read_text(encoding="utf-8")
        ok("Backup", "docs/disaster_recovery.md present")
        if "restore" in dr_text.lower():
            ok("Backup", "Restore steps documented in disaster_recovery.md")
        if "rto" in dr_text.lower() or "RTO" in dr_text:
            ok("Backup", "RTO/RPO targets documented")
    else:
        note("Backup", "MEDIUM", "docs/disaster_recovery.md not found — no documented restore procedure")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print(f"\n{'=' * 60}")
    print("  AUDIT LOG INTEGRITY SUMMARY")
    print("=" * 60)

    if not findings:
        print("  No actionable issues found. Audit log integrity looks good.")
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
    print("DocReview360 Audit Log Integrity Check")
    print(f"Repo root: {REPO_ROOT}")

    check_log_package_structure()
    check_hash_chain()
    check_append_only()
    check_retention_settings()
    check_backup_restore()
    print_summary()

    # Always exit 0 — informational
    sys.exit(0)


if __name__ == "__main__":
    main()
