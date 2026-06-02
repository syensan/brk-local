"""
Tests for BRK sensor statistical analysis.

Tests:
  - Welford mean/std computation
  - Hourly mean computation
  - Anomaly detection via z-score
"""

from __future__ import annotations

import math

import pytest

from brk.sensor.stats import (
    HourlyAccumulator,
    WelfordAccumulator,
    compute_z_score,
)


class TestWelfordAccumulator:
    """Test Welford's online algorithm for mean and variance."""

    def test_empty_accumulator(self) -> None:
        """Empty accumulator has n=0, mean=0, variance=0, std=0."""
        w = WelfordAccumulator()
        assert w.n == 0
        assert w.mean == 0.0
        assert w.variance == 0.0
        assert w.std == 0.0

    def test_single_value(self) -> None:
        """Single value: mean=value, variance=0, std=0."""
        w = WelfordAccumulator()
        w.update(42.0)
        assert w.n == 1
        assert w.mean == 42.0
        assert w.variance == 0.0
        assert w.std == 0.0
        assert w.min_val == 42.0
        assert w.max_val == 42.0

    def test_two_values(self) -> None:
        """Two values: mean=average, variance=(diff/2)^2 for population."""
        w = WelfordAccumulator()
        w.update(10.0)
        w.update(20.0)
        assert w.n == 2
        assert w.mean == 15.0
        # Population variance: ((10-15)^2 + (20-15)^2) / 2 = 25
        assert abs(w.variance - 25.0) < 1e-10
        assert abs(w.std - 5.0) < 1e-10

    def test_three_values(self) -> None:
        """Three values with known mean/std."""
        w = WelfordAccumulator()
        for v in [2.0, 4.0, 6.0]:
            w.update(v)
        assert w.n == 3
        assert w.mean == 4.0
        # Population variance: ((2-4)^2 + (4-4)^2 + (6-4)^2) / 3 = 8/3
        expected_var = 8.0 / 3.0
        assert abs(w.variance - expected_var) < 1e-10

    def test_min_max(self) -> None:
        """Min and max are tracked correctly."""
        w = WelfordAccumulator()
        for v in [5.0, -3.0, 10.0, 0.0, 7.0]:
            w.update(v)
        assert w.min_val == -3.0
        assert w.max_val == 10.0

    def test_numerical_stability(self) -> None:
        """Welford's algorithm is numerically stable for large N."""
        w = WelfordAccumulator()
        n = 100000
        for i in range(n):
            w.update(float(i))

        expected_mean = (n - 1) / 2.0
        assert abs(w.mean - expected_mean) < 1e-6

    def test_to_dict(self) -> None:
        """to_dict returns a properly structured dict."""
        w = WelfordAccumulator()
        w.update(1.0)
        w.update(2.0)
        d = w.to_dict()
        assert d["count"] == 2
        assert d["mean"] == 1.5
        assert d["min"] == 1.0
        assert d["max"] == 2.0


class TestHourlyAccumulator:
    """Test hourly mean computation."""

    def test_empty(self) -> None:
        """Empty accumulator returns all None."""
        h = HourlyAccumulator()
        means = h.get_means()
        assert len(means) == 24
        assert all(v is None for v in means)

    def test_single_hour(self) -> None:
        """Values for a single hour produce the correct mean."""
        h = HourlyAccumulator()
        h.update(5, 10.0)
        h.update(5, 20.0)
        h.update(5, 30.0)
        means = h.get_means()
        assert means[5] == 20.0
        # Other hours are still None
        assert means[0] is None
        assert means[23] is None

    def test_multiple_hours(self) -> None:
        """Values across different hours are tracked independently."""
        h = HourlyAccumulator()
        h.update(0, 100.0)
        h.update(12, 200.0)
        h.update(23, 300.0)
        means = h.get_means()
        assert means[0] == 100.0
        assert means[12] == 200.0
        assert means[23] == 300.0

    def test_out_of_range_hour(self) -> None:
        """Out-of-range hours are silently ignored."""
        h = HourlyAccumulator()
        h.update(-1, 10.0)  # ignored
        h.update(24, 10.0)  # ignored
        h.update(5, 42.0)   # valid
        means = h.get_means()
        assert means[5] == 42.0
        assert means[0] is None


class TestAnomalyDetection:
    """Test z-score based anomaly detection."""

    def test_z_score_zero_std(self) -> None:
        """Z-score is 0 when std is 0."""
        assert compute_z_score(42.0, 42.0, 0.0) == 0.0

    def test_z_score_at_mean(self) -> None:
        """Z-score is 0 when value equals the mean."""
        assert compute_z_score(50.0, 50.0, 10.0) == 0.0

    def test_z_score_one_sigma(self) -> None:
        """Z-score is 1.0 when value is one std from mean."""
        assert abs(compute_z_score(60.0, 50.0, 10.0) - 1.0) < 1e-10

    def test_z_score_three_sigma(self) -> None:
        """Z-score is 3.0 when value is three stds from mean."""
        assert abs(compute_z_score(80.0, 50.0, 10.0) - 3.0) < 1e-10

    def test_z_score_always_positive(self) -> None:
        """compute_z_score returns absolute z-score."""
        # Both 30 and 70 are 2 stds from mean of 50 with std 10
        z_low = compute_z_score(30.0, 50.0, 10.0)
        z_high = compute_z_score(70.0, 50.0, 10.0)
        assert abs(z_low - 2.0) < 1e-10
        assert abs(z_high - 2.0) < 1e-10
