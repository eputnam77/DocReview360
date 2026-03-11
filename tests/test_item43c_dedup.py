# SPDX-License-Identifier: MIT
"""Item 43c: Verify no duplicate (path, method) pairs are registered on the FastAPI app.

These tests import the application and inspect ``app.routes`` to ensure that the
de-duplication work in item 43c did not leave behind any overlapping route
registrations that would cause silent request-routing surprises.
"""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_route_pairs(app) -> list[tuple[str, str]]:
    """Return a flat list of (path, METHOD) pairs for all HTTP routes."""
    pairs: list[tuple[str, str]] = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or not methods:
            continue
        for method in methods:
            pairs.append((path, method.upper()))
    return pairs


def _find_duplicates(pairs: list[tuple[str, str]]) -> dict[tuple[str, str], int]:
    """Return a mapping of (path, method) → count for entries that appear more than once."""
    from collections import Counter
    counts = Counter(pairs)
    return {k: v for k, v in counts.items() if v > 1}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_app():
    """Import and return the FastAPI application."""
    from docreview360.api import app
    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNoDuplicateRoutes:
    """Verify that each (path, method) pair is registered at most once."""

    def test_no_duplicate_http_routes(self, api_app):
        """Assert that no (path, method) combination appears more than once in app.routes."""
        pairs = _collect_route_pairs(api_app)
        duplicates = _find_duplicates(pairs)
        assert not duplicates, (
            f"Found {len(duplicates)} duplicate route registration(s):\n"
            + "\n".join(
                f"  {method} {path!r} registered {count}x"
                for (path, method), count in sorted(duplicates.items())
            )
        )

    def test_routes_count_is_reasonable(self, api_app):
        """Sanity check: the app should have a reasonable number of routes registered."""
        pairs = _collect_route_pairs(api_app)
        # After de-duplication the count should be substantially lower than before.
        # Before: ~500+ unique (path, method) entries; after removal: still well-populated.
        # Just verify we haven't accidentally nuked everything.
        assert len(pairs) >= 100, (
            f"Suspiciously few routes registered: {len(pairs)}. "
            "Check that include_router() calls are still present."
        )

    def test_key_paths_still_reachable(self, api_app):
        """Spot-check that critical paths are still registered (via sub-routers)."""
        pairs_set = {(path, method) for path, method in _collect_route_pairs(api_app)}
        # These paths must exist in the final app (covered by sub-routers)
        required = [
            ("/token", "POST"),
            ("/me", "GET"),
            ("/logout", "POST"),
            ("/users", "GET"),
            ("/profile", "GET"),
            ("/profile", "PUT"),
            ("/rbac/role-permissions", "GET"),
            ("/rbac/matrix", "GET"),
            ("/workflows", "GET"),
            ("/workflows", "POST"),
            ("/approvals", "GET"),
            ("/approvals", "POST"),
            ("/config", "GET"),
            ("/config", "PUT"),
            ("/signature-provider", "GET"),
            ("/signature-provider", "PUT"),
            ("/plugins", "GET"),
            ("/plugins", "POST"),
            ("/plugin-marketplace", "GET"),
        ]
        missing = [f"{method} {path}" for path, method in required if (path, method) not in pairs_set]
        assert not missing, (
            "The following required routes are missing from the app:\n"
            + "\n".join(f"  {r}" for r in missing)
        )

    def test_removed_inline_paths_not_double_registered(self, api_app):
        """Verify that paths moved to sub-routers appear exactly once, not twice."""
        pairs = _collect_route_pairs(api_app)
        duplicates = _find_duplicates(pairs)

        # Paths that were previously duplicated — confirm they are now singular
        formerly_duplicated = [
            ("/token", "POST"),
            ("/me", "GET"),
            ("/logout", "POST"),
            ("/users", "GET"),
            ("/users", "POST"),
            ("/profile", "GET"),
            ("/profile", "PUT"),
            ("/rbac/role-permissions", "GET"),
            ("/rbac/matrix", "GET"),
            ("/workflows", "GET"),
            ("/workflows", "POST"),
            ("/approvals", "GET"),
            ("/approvals", "POST"),
            ("/config", "GET"),
            ("/config", "PUT"),
            ("/plugins", "GET"),
            ("/plugins", "POST"),
            ("/plugin-marketplace", "GET"),
            ("/plugin-marketplace/install", "POST"),
        ]
        still_duped = [
            f"{method} {path}"
            for path, method in formerly_duplicated
            if (path, method) in duplicates
        ]
        assert not still_duped, (
            "The following paths are still registered more than once "
            "(de-duplication incomplete):\n"
            + "\n".join(f"  {r}" for r in still_duped)
        )
