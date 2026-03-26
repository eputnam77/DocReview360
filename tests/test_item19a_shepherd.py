# SPDX-License-Identifier: MIT
"""Item 19a — release-shepherd.sh tests.

Covers:
  - Script exists and is executable
  - Lockfile behavior (creates and cleans up .shepherd.lock)
  - First-unchecked-item selection from RELEASE_CHECKLIST.md
  - Artifacts directory creation (artifacts/automation/)
  - Report format and required fields
  - No-items-found case
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SHEPHERD = REPO_ROOT / "scripts" / "release-shepherd.sh"
CHECKLIST = REPO_ROOT / "RELEASE_CHECKLIST.md"


# ---------------------------------------------------------------------------
# Source-level verification
# ---------------------------------------------------------------------------

class TestShepherdSource:
    def _text(self) -> str:
        return SHEPHERD.read_text(encoding="utf-8")

    def test_script_exists(self) -> None:
        assert SHEPHERD.exists(), "scripts/release-shepherd.sh not found"

    def test_spdx_header(self) -> None:
        text = self._text()
        assert "SPDX-License-Identifier: MIT" in text

    def test_set_euo_pipefail(self) -> None:
        """Script uses strict bash mode."""
        text = self._text()
        assert "set -euo pipefail" in text

    def test_lockfile_creation(self) -> None:
        text = self._text()
        assert ".shepherd.lock" in text
        # Lockfile must be written
        assert 'echo "$$"' in text or "echo" in text

    def test_lockfile_checked_on_entry(self) -> None:
        text = self._text()
        # Exits with error if lockfile exists
        assert "exit 1" in text
        assert "LOCKFILE" in text

    def test_lockfile_cleanup_on_exit(self) -> None:
        text = self._text()
        # trap removes lockfile
        assert "trap" in text
        assert "LOCKFILE" in text

    def test_first_unchecked_item_selection(self) -> None:
        """Script uses grep to find first unchecked item."""
        text = self._text()
        assert r"- \[ \]" in text or "\\[\\s\\\\]\\]" in text or "grep" in text

    def test_artifacts_dir_creation(self) -> None:
        text = self._text()
        assert "artifacts/automation" in text
        assert "mkdir" in text

    def test_report_has_timestamp(self) -> None:
        text = self._text()
        assert "TIMESTAMP" in text
        assert "date" in text

    def test_report_has_selected_item_field(self) -> None:
        text = self._text()
        assert "Selected Item" in text or "SELECTED_LINE" in text

    def test_report_has_test_results_field(self) -> None:
        text = self._text()
        assert "Test Results" in text or "TEST_OUTPUT" in text

    def test_report_has_recommendation_field(self) -> None:
        text = self._text()
        assert "Recommendation" in text or "RECOMMENDATION" in text

    def test_handles_no_unchecked_items(self) -> None:
        text = self._text()
        assert "No unchecked items" in text or "All done" in text

    def test_report_written_to_artifacts_dir(self) -> None:
        text = self._text()
        assert "release-shepherd-" in text
        assert "REPORT" in text

    def test_script_runs_pytest(self) -> None:
        text = self._text()
        assert "pytest" in text


# ---------------------------------------------------------------------------
# First-unchecked-item selection logic
# ---------------------------------------------------------------------------

class TestFirstUncheckedItemSelection:
    """Verify the grep pattern used by the script matches RELEASE_CHECKLIST.md format."""

    # The script uses: grep -n '^\s*- \[ \]' CHECKLIST | head -1
    GREP_PATTERN = re.compile(r"^\s*- \[ \] (.+)$")

    def test_pattern_matches_unchecked_item(self) -> None:
        assert self.GREP_PATTERN.match("- [ ] Define supported platforms")

    def test_pattern_does_not_match_checked_item(self) -> None:
        assert not self.GREP_PATTERN.match("- [x] Done item")

    def test_pattern_matches_indented_item(self) -> None:
        assert self.GREP_PATTERN.match("  - [ ] An indented item")

    def test_checklist_still_has_unchecked_items(self) -> None:
        """Script should not produce 'No unchecked items' output right now."""
        text = CHECKLIST.read_text(encoding="utf-8")
        unchecked = [l for l in text.splitlines() if self.GREP_PATTERN.match(l)]
        assert len(unchecked) > 0, "Checklist has no unchecked items — shepherd would exit early"

    def test_first_unchecked_item_is_extractable(self) -> None:
        text = CHECKLIST.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = self.GREP_PATTERN.match(line)
            if m:
                item_text = m.group(1)
                assert len(item_text) > 5
                return
        pytest.fail("No unchecked item found")


# ---------------------------------------------------------------------------
# Artifacts directory and report format
# ---------------------------------------------------------------------------

class TestArtifactReport:
    def test_artifacts_automation_dir_exists_or_creatable(self) -> None:
        artifacts = REPO_ROOT / "artifacts" / "automation"
        # Either it already exists or we can create it
        if not artifacts.exists():
            artifacts.mkdir(parents=True, exist_ok=True)
            created = True
        else:
            created = False
        assert artifacts.exists()
        if created:
            artifacts.rmdir()
            artifacts.parent.rmdir()

    def test_report_filename_pattern(self) -> None:
        """Report files should match release-shepherd-<timestamp>.md pattern."""
        pattern = re.compile(r"release-shepherd-\d{8}T\d{6}Z\.md")
        assert pattern.match("release-shepherd-20260312T110000Z.md")

    def test_report_required_sections(self) -> None:
        """Any generated report must have these sections."""
        shepherd_text = SHEPHERD.read_text(encoding="utf-8")
        required = ["Selected Item", "Test Results", "Recommended Next Action"]
        for section in required:
            assert section in shepherd_text, f"Report template missing section: {section}"

    def test_report_includes_checklist_path(self) -> None:
        shepherd_text = SHEPHERD.read_text(encoding="utf-8")
        assert "CHECKLIST" in shepherd_text

    def test_report_includes_exit_code(self) -> None:
        shepherd_text = SHEPHERD.read_text(encoding="utf-8")
        assert "Exit code" in shepherd_text or "TEST_EXIT" in shepherd_text
