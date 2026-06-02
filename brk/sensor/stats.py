"""
Statistical analysis for BRK-Sensor Profile v0.1.

Implements Welford's online algorithm for computing mean and variance
in a single streaming pass, without loading all data into memory.

Also computes hourly means and detects z-score anomalies.

IMPORTANT: BRK is NOT a universal lossless compressor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from brk.constants import FLOAT_PRECISION


def round_float(v: float, precision: int = FLOAT_PRECISION) -> float:
    """Round a float to the specified precision."""
    return round(v, precision)


@dataclass
class WelfordAccumulator:
    """Online mean and variance accumulator using Welford's algorithm.

    Numerically stable single-pass computation.
    """

    n: int = 0
    mean: float = 0.0
    m2: float = 0.0  # sum of squared deviations
    min_val: float = float("inf")
    max_val: float = float("-inf")

    def update(self, x: float) -> None:
        """Add a new observation."""
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2
        if x < self.min_val:
            self.min_val = x
        if x > self.max_val:
            self.max_val = x

    @property
    def variance(self) -> float:
        """Population variance."""
        if self.n < 2:
            return 0.0
        return self.m2 / self.n

    @property
    def std(self) -> float:
        """Population standard deviation."""
        return math.sqrt(self.variance)

    def to_dict(self) -> dict[str, Any]:
        """Export as a dictionary with rounded values."""
        return {
            "count": self.n,
            "mean": round_float(self.mean),
            "std": round_float(self.std),
            "min": round_float(self.min_val) if self.n > 0 else None,
            "max": round_float(self.max_val) if self.n > 0 else None,
        }


@dataclass
class MetricStats:
    """Complete statistics for a single metric within a sensor group."""

    count: int = 0
    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    first: float = 0.0
    last: float = 0.0
    slope_per_second: float = 0.0
    hourly_mean: list[float | None] = field(default_factory=lambda: [None] * 24)

    def to_dict(self) -> dict[str, Any]:
        """Export as a dictionary with rounded values."""
        return {
            "count": self.count,
            "mean": round_float(self.mean),
            "std": round_float(self.std),
            "min": round_float(self.min),
            "max": round_float(self.max),
            "first": round_float(self.first),
            "last": round_float(self.last),
            "slope_per_second": round_float(self.slope_per_second),
            "hourly_mean": [
                round_float(v) if v is not None else None for v in self.hourly_mean
            ],
        }


@dataclass
class HourlyAccumulator:
    """Accumulator for hourly mean computation.

    Maintains a sum and count for each of the 24 hours.
    """

    sums: list[float] = field(default_factory=lambda: [0.0] * 24)
    counts: list[int] = field(default_factory=lambda: [0] * 24)

    def update(self, hour: int, value: float) -> None:
        """Add a value for the given hour (0-23)."""
        if 0 <= hour <= 23:
            self.sums[hour] += value
            self.counts[hour] += 1

    def get_means(self) -> list[float | None]:
        """Return the mean for each hour, or None if no data."""
        return [
            self.sums[h] / self.counts[h] if self.counts[h] > 0 else None
            for h in range(24)
        ]


@dataclass
class AnomalyCandidate:
    """A z-score anomaly candidate."""

    sensor_id: str
    metric: str
    t_offset_s: int
    value: float
    z: float


def compute_z_score(value: float, mean: float, std: float) -> float:
    """Compute the absolute z-score of a value.

    Returns 0.0 if std is 0 (no variation).
    """
    if std == 0.0:
        return 0.0
    return abs(value - mean) / std
