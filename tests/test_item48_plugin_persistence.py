# SPDX-License-Identifier: MIT
"""Tests for Item 48: persist built-in plugin toggle state to SQLite."""

from __future__ import annotations

import pytest
from docreview360 import db_store, plugin_marketplace
from docreview360.models import BuiltinPluginStateRecord


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Each test gets a fresh SQLite DB; in-memory cache is reset between tests."""
    db_store.reset_db(f"sqlite:///{tmp_path / 'test_item48.db'}")
    # Reset in-memory cache to defaults before each test.
    with plugin_marketplace._builtin_lock:
        plugin_marketplace._builtin_states.clear()
        plugin_marketplace._builtin_states.update(plugin_marketplace._DEFAULT_BUILTIN_STATES)
    yield
    with plugin_marketplace._builtin_lock:
        plugin_marketplace._builtin_states.clear()
        plugin_marketplace._builtin_states.update(plugin_marketplace._DEFAULT_BUILTIN_STATES)
    db_store.reset_db(None)


# ---------------------------------------------------------------------------
# get_builtin_status — default state (no DB records)
# ---------------------------------------------------------------------------


def test_get_builtin_status_defaults_when_no_records() -> None:
    """When the DB has no records all built-in plugins should default to True."""
    status = plugin_marketplace.get_builtin_status()
    assert status == {"fedstylevalidator": True, "scdocbuilder": True}


def test_get_builtin_status_returns_both_plugins() -> None:
    """get_builtin_status always returns an entry for every BUILTIN_PLUGIN_ID."""
    status = plugin_marketplace.get_builtin_status()
    assert set(status.keys()) == plugin_marketplace.BUILTIN_PLUGIN_IDS


def test_get_builtin_status_ignores_stale_memory_when_db_has_no_records() -> None:
    """A healthy empty DB should use builtin defaults, not stale in-memory fallback state."""
    with plugin_marketplace._builtin_lock:
        plugin_marketplace._builtin_states["scdocbuilder"] = False

    status = plugin_marketplace.get_builtin_status()

    assert status == {"fedstylevalidator": True, "scdocbuilder": True}


# ---------------------------------------------------------------------------
# set_builtin_plugin_state — persistence to DB
# ---------------------------------------------------------------------------


def test_set_persists_to_db() -> None:
    """set_builtin_plugin_state writes a row to the builtin_plugin_states table."""
    plugin_marketplace.set_builtin_plugin_state("fedstylevalidator", False)

    db = db_store.get_db()
    with db.orm_session() as session:
        record = session.get(BuiltinPluginStateRecord, "fedstylevalidator")
    assert record is not None
    assert record.enabled is False


def test_set_then_get_returns_updated_state() -> None:
    """After disabling a plugin get_builtin_status reflects the change."""
    plugin_marketplace.set_builtin_plugin_state("fedstylevalidator", False)
    status = plugin_marketplace.get_builtin_status()
    assert status["fedstylevalidator"] is False
    assert status["scdocbuilder"] is True


def test_set_re_enables_plugin() -> None:
    """A plugin can be disabled then re-enabled."""
    plugin_marketplace.set_builtin_plugin_state("scdocbuilder", False)
    plugin_marketplace.set_builtin_plugin_state("scdocbuilder", True)
    status = plugin_marketplace.get_builtin_status()
    assert status["scdocbuilder"] is True


def test_set_unknown_plugin_raises_value_error() -> None:
    """Calling set_builtin_plugin_state with an unknown ID raises ValueError."""
    with pytest.raises(ValueError, match="Unknown built-in plugin"):
        plugin_marketplace.set_builtin_plugin_state("nonexistent-plugin", False)


# ---------------------------------------------------------------------------
# Persistence across simulated restart (clear in-memory cache, read from DB)
# ---------------------------------------------------------------------------


def test_state_persists_across_simulated_restart() -> None:
    """State written to DB survives an in-memory cache clear (simulated restart)."""
    plugin_marketplace.set_builtin_plugin_state("fedstylevalidator", False)

    # Simulate a server restart by wiping the in-memory cache back to defaults.
    with plugin_marketplace._builtin_lock:
        for pid in plugin_marketplace.BUILTIN_PLUGIN_IDS:
            plugin_marketplace._builtin_states[pid] = True

    # get_builtin_status must re-read from DB and return the persisted state.
    status = plugin_marketplace.get_builtin_status()
    assert status["fedstylevalidator"] is False
    assert status["scdocbuilder"] is True  # unchanged, still default True in DB


def test_multiple_plugins_persist_independently() -> None:
    """Independent toggle states for multiple plugins are each persisted correctly."""
    plugin_marketplace.set_builtin_plugin_state("fedstylevalidator", False)
    plugin_marketplace.set_builtin_plugin_state("scdocbuilder", False)

    # Wipe in-memory cache.
    with plugin_marketplace._builtin_lock:
        for pid in plugin_marketplace.BUILTIN_PLUGIN_IDS:
            plugin_marketplace._builtin_states[pid] = True

    status = plugin_marketplace.get_builtin_status()
    assert status["fedstylevalidator"] is False
    assert status["scdocbuilder"] is False


# ---------------------------------------------------------------------------
# DB fallback: in-memory state used when DB is unavailable
# ---------------------------------------------------------------------------


def test_get_builtin_status_falls_back_to_memory_on_db_error(monkeypatch) -> None:
    """get_builtin_status returns in-memory state if the DB raises an exception."""
    # Pre-set an in-memory state that differs from the DB default.
    with plugin_marketplace._builtin_lock:
        plugin_marketplace._builtin_states["fedstylevalidator"] = False

    # Make get_db raise so the DB path is unavailable.
    monkeypatch.setattr(
        plugin_marketplace,
        "get_db",
        lambda: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    status = plugin_marketplace.get_builtin_status()
    assert status["fedstylevalidator"] is False  # in-memory fallback value


def test_set_builtin_plugin_state_falls_back_to_memory_on_db_error(monkeypatch) -> None:
    """set_builtin_plugin_state still updates in-memory state when DB is unavailable."""
    monkeypatch.setattr(
        plugin_marketplace,
        "get_db",
        lambda: (_ for _ in ()).throw(RuntimeError("db down")),
    )

    plugin_marketplace.set_builtin_plugin_state("scdocbuilder", False)
    # In-memory cache must reflect the change even though DB write failed.
    assert plugin_marketplace._builtin_states["scdocbuilder"] is False
