"""Rolling FPS statistics: average and low-percentile frame rates.

Backends only report an instantaneous FPS/frametime. To show 1% and 0.1% lows
(and a windowed average) we keep a short ring buffer of the most recent FPS
samples and derive the statistics from it.
"""
from __future__ import annotations

from collections import deque


def percentile(sorted_values: list[float], pct: float) -> float:
    """Return the pct-th percentile (0..100) of an already-sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    frac = rank - low
    return sorted_values[low] * (1 - frac) + sorted_values[high] * frac


class FPSStats:
    """Ring buffer of FPS samples with derived average and low percentiles."""

    def __init__(self, window: int = 300):
        self.window = max(2, int(window))
        self._samples: deque[float] = deque(maxlen=self.window)

    def reset(self) -> None:
        self._samples.clear()

    def add(self, fps: float | None) -> None:
        if fps is None:
            return
        try:
            value = float(fps)
        except (TypeError, ValueError):
            return
        if value > 0:
            self._samples.append(value)

    def __len__(self) -> int:
        return len(self._samples)

    def summary(self) -> dict:
        if not self._samples:
            return {}
        ordered = sorted(self._samples)
        avg = sum(ordered) / len(ordered)
        return {
            "fps_avg": round(avg, 1),
            "fps_1low": round(percentile(ordered, 1.0), 1),
            "fps_01low": round(percentile(ordered, 0.1), 1),
        }
