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
    from .signature_anomaly import (  # noqa: F401
        MODEL_NAME,
        MODEL_PATH,
        MODEL_VERSION,
        export_signature_anomaly_model,
        get_signature_anomaly_metadata,
        score_signature_anomaly,
    )
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
    from .routing_critic import (
        ROUTING_FEATURE_NAMES,
        RoutingCritic,
        RoutingExample,
        export_routing_critic_to_onnx,
        routing_feature_vector,
        train_routing_critic,
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

_ROUTING_EXPORTS = {
    "ROUTING_FEATURE_NAMES",
    "RoutingCritic",
    "RoutingExample",
    "export_routing_critic_to_onnx",
    "routing_feature_vector",
    "train_routing_critic",
}

_ANOMALY_EXPORTS = {
    "MODEL_NAME",
    "MODEL_PATH",
    "MODEL_VERSION",
    "export_signature_anomaly_model",
    "get_signature_anomaly_metadata",
    "score_signature_anomaly",
}

__all__ += sorted(_TORCH_EXPORTS | _ROUTING_EXPORTS | _ANOMALY_EXPORTS)


def __getattr__(name: str) -> Any:
    if name in _TORCH_EXPORTS:
        from . import torch_models

        return getattr(torch_models, name)
    if name in _ROUTING_EXPORTS:
        from . import routing_critic

        return getattr(routing_critic, name)
    if name in _ANOMALY_EXPORTS:
        from . import signature_anomaly

        return getattr(signature_anomaly, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
