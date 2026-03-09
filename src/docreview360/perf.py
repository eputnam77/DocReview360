"""Performance measurement helpers."""

from __future__ import annotations

import time



def measure_typing_time(char_count: int = 100) -> float:
    """Simulate typing ``char_count`` characters and return elapsed seconds."""
    if char_count <= 0:
        raise ValueError("char_count must be positive")
    start = time.perf_counter()
    for _ in range(char_count):
        time.sleep(0)
    duration = time.perf_counter() - start
    return duration
