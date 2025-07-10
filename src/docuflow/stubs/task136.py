"""Celery Flower launcher wrapper."""

from celery import Celery

from ..flower import launch_flower


async def task136(app: Celery) -> None:
    """Start Flower for the given Celery app."""
    await launch_flower(app)
