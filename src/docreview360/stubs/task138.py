"""API docs and SDK generation helper."""

from ..scripts.generate_sdk import generate


def task138(output: str = "packages/sdk-ts") -> None:
    """Generate the SDK using the helper script."""
    generate(output)
