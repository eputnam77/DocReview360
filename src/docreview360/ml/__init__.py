"""Machine learning helpers for DocReview360."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .onnx_infer import (
    ModelMetadata,
    clear_session_cache,
    get_model_metadata,
    get_session,
    infer,
)

__all__ = [
    "ModelMetadata",
    "clear_session_cache",
    "get_model_metadata",
    "get_session",
    "infer",
]

if TYPE_CHECKING:  # pragma: no cover - used for type checkers only
    from .torch_models import (
        CriticConfig,
        TinyCritic,
        build_clarity_critic,
        build_compliance_critic,
        build_impact_critic,
        build_risk_critic,
        critic_builders,
        export_critic_to_onnx,
        get_default_critics,
        load_critic,
        save_critic,
        train_critic,
        update_critic,
    )

_TORCH_EXPORTS = {
    "CriticConfig",
    "TinyCritic",
    "build_clarity_critic",
    "build_compliance_critic",
    "build_impact_critic",
    "build_risk_critic",
    "critic_builders",
    "export_critic_to_onnx",
    "get_default_critics",
    "load_critic",
    "save_critic",
    "train_critic",
    "update_critic",
}

__all__ += sorted(_TORCH_EXPORTS)


def __getattr__(name: str) -> Any:
    if name in _TORCH_EXPORTS:
        from . import torch_models

        return getattr(torch_models, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
