# SPDX-License-Identifier: MIT
"""Per-phase SLA (Service Level Agreement) tracking.

Allows administrators to define maximum and warning durations for each workflow
phase.  The SLA data is persisted to a JSON file so it survives restarts.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import BaseModel, Field

_SLA_FILE = Path(os.getenv("DOCREVIEW360_PHASE_SLA_FILE", "phase_sla.json"))
_LOCK = RLock()
_logger = logging.getLogger(__name__)

# In-memory store: phase_name -> SLAConfig
_SLA_STORE: dict[str, "PhaseSLAConfig"] = {}
_LOADED = False


class PhaseSLAConfig(BaseModel):
    """SLA configuration for a single workflow phase."""

    phase: str = Field(description="Phase name")
    max_days: int = Field(gt=0, description="Maximum days allowed in this phase before breach")
    warning_days: int = Field(
        ge=0, description="Days remaining before max_days to emit a warning"
    )

    def model_post_init(self, __context: Any) -> None:
        if self.warning_days >= self.max_days:
            raise ValueError("warning_days must be less than max_days")


class PhaseSLAStatus(BaseModel):
    """Current SLA status for a phase."""

    phase: str
    max_days: int
    warning_days: int
    elapsed_days: int | None = None
    status: str = Field(
        description="One of: ok, warning, breached, unknown (no SLA configured)"
    )
    breach_in_days: int | None = None


def _load() -> None:
    """Load SLA config from disk into the in-memory store."""

    global _LOADED
    if _LOADED:
        return
    _SLA_STORE.clear()
    if _SLA_FILE.exists():
        try:
            raw = json.loads(_SLA_FILE.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for phase, cfg in raw.items():
                    try:
                        _SLA_STORE[phase] = PhaseSLAConfig(**cfg)
                    except Exception as exc:
                        _logger.debug("Skipping invalid SLA entry for phase %r: %s", phase, exc)
        except Exception as exc:
            _logger.warning("Failed to load SLA config from %s: %s", _SLA_FILE, exc)
    _LOADED = True


def _persist() -> None:
    """Persist the in-memory SLA store to disk."""

    _SLA_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {phase: cfg.model_dump() for phase, cfg in _SLA_STORE.items()}
    _SLA_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def set_phase_sla(phase: str, max_days: int, warning_days: int) -> PhaseSLAConfig:
    """Create or update the SLA configuration for ``phase``."""

    cfg = PhaseSLAConfig(phase=phase, max_days=max_days, warning_days=warning_days)
    with _LOCK:
        _load()
        _SLA_STORE[phase] = cfg
        _persist()
    return cfg


def get_phase_sla(phase: str) -> PhaseSLAConfig | None:
    """Return the SLA configuration for ``phase``, or ``None`` if unset."""

    with _LOCK:
        _load()
        return _SLA_STORE.get(phase)


def get_all_phase_slas() -> dict[str, PhaseSLAConfig]:
    """Return all configured SLAs keyed by phase name."""

    with _LOCK:
        _load()
        return dict(_SLA_STORE)


def delete_phase_sla(phase: str) -> bool:
    """Remove SLA config for ``phase``.  Returns ``True`` if it existed."""

    with _LOCK:
        _load()
        existed = phase in _SLA_STORE
        if existed:
            del _SLA_STORE[phase]
            _persist()
        return existed


def evaluate_phase_sla(phase: str, elapsed_days: int) -> PhaseSLAStatus:
    """Evaluate the SLA status for ``phase`` given ``elapsed_days``.

    Parameters
    ----------
    phase:
        Workflow phase name.
    elapsed_days:
        Number of days the document has been in this phase.

    Returns
    -------
    PhaseSLAStatus
        Current SLA status.  ``status`` is ``"unknown"`` when no SLA is
        configured for the phase.
    """

    cfg = get_phase_sla(phase)
    if cfg is None:
        return PhaseSLAStatus(phase=phase, max_days=0, warning_days=0, status="unknown")

    breach_in = cfg.max_days - elapsed_days
    if elapsed_days >= cfg.max_days:
        status = "breached"
    elif elapsed_days >= (cfg.max_days - cfg.warning_days):
        status = "warning"
    else:
        status = "ok"

    return PhaseSLAStatus(
        phase=phase,
        max_days=cfg.max_days,
        warning_days=cfg.warning_days,
        elapsed_days=elapsed_days,
        status=status,
        breach_in_days=max(breach_in, 0),
    )


def clear_sla_store() -> None:
    """Remove all SLA configurations (used in tests)."""

    global _LOADED
    with _LOCK:
        _SLA_STORE.clear()
        _LOADED = True
        if _SLA_FILE.exists():
            _SLA_FILE.unlink()
