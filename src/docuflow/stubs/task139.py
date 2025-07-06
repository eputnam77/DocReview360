"""Feature flag helper."""

from ..feature_flags import FeatureFlags


def task139(url: str, api_key: str, name: str) -> bool:
    """Return flag state using ``FeatureFlags`` wrapper."""
    flags = FeatureFlags(url, api_key)
    return flags.is_enabled(name)
