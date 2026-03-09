"""Helm chart smoke test script."""

from __future__ import annotations

import subprocess
from pathlib import Path

import httpx



async def run() -> None:
    """Install the chart in KIND and run health checks."""
    chart_path = Path("helm")
    subprocess.run(["helm", "install", "docreview360", str(chart_path)], check=True)
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost/health", timeout=10)
        resp.raise_for_status()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
