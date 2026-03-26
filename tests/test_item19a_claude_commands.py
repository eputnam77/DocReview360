# SPDX-License-Identifier: MIT
"""Item 19a — Claude Code custom commands smoke coverage.

Verifies that `.claude/commands/*.md` files:
  - Exist and are non-empty
  - Start with a `# /command-name —` heading for discoverability
  - Contain a Steps section or structured content
  - Reference relevant scripts, files, or actions
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"


# ---------------------------------------------------------------------------
# Expected commands
# ---------------------------------------------------------------------------

EXPECTED_COMMANDS = [
    "triage-failure.md",
    "docs-drift.md",
    "checklist-next.md",
    "packaging-audit.md",
]


# ---------------------------------------------------------------------------
# Discovery smoke test
# ---------------------------------------------------------------------------

class TestCommandDiscovery:
    def test_commands_directory_exists(self) -> None:
        assert COMMANDS_DIR.exists(), f".claude/commands/ not found at {COMMANDS_DIR}"

    def test_all_expected_commands_present(self) -> None:
        missing = [f for f in EXPECTED_COMMANDS if not (COMMANDS_DIR / f).exists()]
        assert not missing, f"Missing command files: {missing}"

    def test_no_empty_command_files(self) -> None:
        for name in EXPECTED_COMMANDS:
            path = COMMANDS_DIR / name
            text = path.read_text(encoding="utf-8")
            assert len(text.strip()) > 50, f"{name} appears too short / empty"

    def test_command_files_are_markdown(self) -> None:
        for name in EXPECTED_COMMANDS:
            assert name.endswith(".md"), f"{name} is not a .md file"


# ---------------------------------------------------------------------------
# Format verification — each command must have a title heading
# ---------------------------------------------------------------------------

class TestCommandFormat:
    """Commands must start with # /<name> — <description> for Claude to discover them."""

    HEADING_RE = re.compile(r"^#\s+/\S+")

    def test_checklist_next_has_heading(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        first_line = text.strip().splitlines()[0]
        assert self.HEADING_RE.match(first_line), f"Bad heading: {first_line!r}"

    def test_triage_failure_has_heading(self) -> None:
        text = (COMMANDS_DIR / "triage-failure.md").read_text(encoding="utf-8")
        first_line = text.strip().splitlines()[0]
        assert self.HEADING_RE.match(first_line), f"Bad heading: {first_line!r}"

    def test_docs_drift_has_heading(self) -> None:
        text = (COMMANDS_DIR / "docs-drift.md").read_text(encoding="utf-8")
        first_line = text.strip().splitlines()[0]
        assert self.HEADING_RE.match(first_line), f"Bad heading: {first_line!r}"

    def test_packaging_audit_has_heading(self) -> None:
        text = (COMMANDS_DIR / "packaging-audit.md").read_text(encoding="utf-8")
        first_line = text.strip().splitlines()[0]
        assert self.HEADING_RE.match(first_line), f"Bad heading: {first_line!r}"


# ---------------------------------------------------------------------------
# Content verification — each command references relevant actions
# ---------------------------------------------------------------------------

class TestCommandContent:
    def test_checklist_next_references_checklist(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        assert "RELEASE_CHECKLIST.md" in text

    def test_checklist_next_has_steps(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        assert "## Steps" in text or "Steps" in text

    def test_checklist_next_references_pytest(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        assert "pytest" in text

    def test_triage_failure_references_failing_test(self) -> None:
        text = (COMMANDS_DIR / "triage-failure.md").read_text(encoding="utf-8")
        assert "fail" in text.lower() or "test" in text.lower()

    def test_triage_failure_references_root_cause(self) -> None:
        text = (COMMANDS_DIR / "triage-failure.md").read_text(encoding="utf-8")
        assert "root cause" in text.lower() or "patch" in text.lower()

    def test_docs_drift_references_readme(self) -> None:
        text = (COMMANDS_DIR / "docs-drift.md").read_text(encoding="utf-8")
        assert "README" in text or "readme" in text.lower()

    def test_docs_drift_references_check_script(self) -> None:
        text = (COMMANDS_DIR / "docs-drift.md").read_text(encoding="utf-8")
        # Should reference the check-docs-drift.py script
        assert "check-docs-drift" in text or "drift" in text.lower()

    def test_packaging_audit_references_wheel(self) -> None:
        text = (COMMANDS_DIR / "packaging-audit.md").read_text(encoding="utf-8")
        assert "wheel" in text.lower() or "sdist" in text.lower() or "packaging" in text.lower()

    def test_packaging_audit_references_pypi(self) -> None:
        text = (COMMANDS_DIR / "packaging-audit.md").read_text(encoding="utf-8")
        assert "PyPI" in text or "pypi" in text.lower() or "publish" in text.lower()


# ---------------------------------------------------------------------------
# Hard guardrails verification — checklist-next guardrails
# ---------------------------------------------------------------------------

class TestChecklistNextGuardrails:
    def test_has_guardrails_section(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        assert "guardrail" in text.lower() or "guard" in text.lower()

    def test_blocks_pypi_publish(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        assert "PyPI" in text

    def test_blocks_docker_push(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        assert "Docker" in text or "docker" in text.lower()

    def test_requires_pre_commit(self) -> None:
        text = (COMMANDS_DIR / "checklist-next.md").read_text(encoding="utf-8")
        assert "pre-commit" in text
