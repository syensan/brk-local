"""
Sensor data schema definitions for BRK-Sensor Profile v0.1.

Defines the data structures used in semantic_graph, sparse_residual,
procedural_seed, and task_outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brk.constants import DECODER_NAME, FLOAT_PRECISION
from brk.sensor.stats import round_float


@dataclass
class SensorMetricEntry:
    """A single metric's statistics within a sensor entry."""

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
class SensorEntry:
    """A single sensor's data within the semantic graph."""

    start_offset_s: int = 0
    end_offset_s: int = 0
    n: int = 0
    metrics: dict[str, SensorMetricEntry] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_offset_s": self.start_offset_s,
            "end_offset_s": self.end_offset_s,
            "n": self.n,
            "metrics": {k: v.to_dict() for k, v in self.metrics.items()},
        }


@dataclass
class AnomalyEntry:
    """A single anomaly point in the sparse residual."""

    sensor_id: str = ""
    metric: str = ""
    t_s: int = 0  # offset seconds from time_origin
    value: float = 0.0
    z: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "metric": self.metric,
            "t_s": self.t_s,
            "value": round_float(self.value),
            "z": round_float(self.z),
        }


def build_semantic_graph(
    time_origin: str,
    duration_s: int,
    sensor_count: int,
    record_count: int,
    metrics: list[str],
    sensors: dict[str, SensorEntry],
    anomalies: list[AnomalyEntry],
) -> dict[str, Any]:
    """Build the semantic_graph field for the BRK container."""
    return {
        "type": "sensor_timeseries_graph",
        "time_origin": time_origin,
        "duration_s": duration_s,
        "sensor_count": sensor_count,
        "record_count": record_count,
        "metrics": metrics,
        "sensors": {k: v.to_dict() for k, v in sensors.items()},
        "anomalies": [a.to_dict() for a in anomalies],
    }


def build_task_outputs(
    sensor_count: int,
    metric_count: int,
    record_count: int,
    duration_s: int,
    anomaly_count: int,
) -> dict[str, Any]:
    """Build the task_outputs field for the BRK container."""
    return {
        "sensor_count": sensor_count,
        "metric_count": metric_count,
        "record_count": record_count,
        "duration_s": duration_s,
        "anomaly_count": anomaly_count,
    }


def build_sparse_residual(anomalies: list[AnomalyEntry]) -> dict[str, Any]:
    """Build the sparse_residual field for the BRK container."""
    return {
        "anomalies": [a.to_dict() for a in anomalies],
    }


def build_procedural_seed(seed: int = 0) -> dict[str, Any]:
    """Build the procedural_seed field for the BRK container."""
    return {
        "generator": "deterministic_sensor_timeseries_reconstructor",
        "seed": seed,
    }
