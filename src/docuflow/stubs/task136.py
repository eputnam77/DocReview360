"""Celery Flower launcher wrapper."""

from ..flower import launch_flower


async def task136(app) -> None:
    """Start Flower for the given Celery app."""
    await launch_flower(app)
