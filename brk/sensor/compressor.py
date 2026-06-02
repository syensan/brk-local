"""
BRK-Sensor compressor implementation.

Two-pass streaming compression:
  Pass 1: Compute per-sensor, per-metric statistics using Welford's algorithm,
          hourly means, and first/last values.
  Pass 2: Detect z-score anomalies using Pass 1 statistics.

Does NOT load the entire CSV into memory.

IMPORTANT: .brk is NOT a universal lossless compressor.
BRK stores a contract-bound semantic specification for acceptable reconstruction.
"""

from __future__ import annotations

import heapq
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from brk.constants import (
    BUDGET_LEVEL_DROP_HOURLY,
    BUDGET_LEVEL_FAILURE,
    BUDGET_LEVEL_FULL,
    BUDGET_LEVEL_HALF_ANOMALIES,
    BUDGET_LEVEL_REDUCE_ANOMALIES,
    BUDGET_LEVEL_ROUND_HOURLY,
    DEFAULT_ANOMALY_Z_THRESHOLD,
    DEFAULT_BUDGET_BYTES,
    DEFAULT_MAX_ANOMALIES,
    FLAG_BIT_EXACT_RECONSTRUCTION,
    FLAG_LOSSLESS,
    FLAG_SEMANTIC_EQUIVALENT,
    FORMAT_VERSION,
    MAGIC_STR,
    PROFILE_SENSOR,
    CREATED_BY,
)
from brk.container import build_header, build_model_binding, write_brk
from brk.checksum import build_semantic_checksum_field
from brk.contracts import BRKContract, default_contract
from brk.errors import BudgetExceededError, CSVSchemaError
from brk.sensor.csv_reader import (
    detect_columns,
    detect_metric_columns,
    get_csv_header,
    stream_csv_rows,
    try_parse_float,
)
from brk.sensor.schema import (
    AnomalyEntry,
    SensorEntry,
    SensorMetricEntry,
    build_procedural_seed,
    build_semantic_graph,
    build_sparse_residual,
    build_task_outputs,
)
from brk.sensor.stats import (
    HourlyAccumulator,
    WelfordAccumulator,
    compute_z_score,
)
from brk.util.json import canonical_encode
from brk.util.time import (
    datetime_to_offset_seconds,
    format_utc_timestamp,
    now_utc_iso,
    parse_utc_timestamp,
)
from brk.util.size import format_size, within_budget


def compress_sensor(
    csv_path: Path,
    output_path: Path,
    contract_json: dict[str, Any] | None = None,
    budget: int = DEFAULT_BUDGET_BYTES,
    max_anomalies: int = DEFAULT_MAX_ANOMALIES,
    anomaly_z: float = DEFAULT_ANOMALY_Z_THRESHOLD,
    strict_budget: bool = False,
) -> dict[str, Any]:
    """Compress a sensor CSV into a .brk container.

    Two-pass streaming algorithm. Returns a report dict with
    output_size_bytes, target_budget_bytes, within_budget, etc.

    BRK is NOT a universal lossless compressor.
    """
    csv_path = Path(csv_path)
    output_path = Path(output_path)

    # ── Detect columns ──────────────────────────────────────────────────
    header = get_csv_header(csv_path)
    detect_columns(header)  # validates required columns
    metric_cols = detect_metric_columns(csv_path)

    if not metric_cols:
        raise CSVSchemaError(
            "No metric columns detected. "
            "At least one numeric column (other than ts, sensor_id) is required."
        )

    # ── Build or load contract ──────────────────────────────────────────
    if contract_json is not None:
        contract = BRKContract.from_dict(contract_json)
    else:
        contract = default_contract()

    # ── Pass 1: Statistics ──────────────────────────────────────────────
    # Per-sensor, per-metric accumulators
    welford: dict[str, dict[str, WelfordAccumulator]] = {}
    hourly: dict[str, dict[str, HourlyAccumulator]] = {}
    first_values: dict[str, dict[str, float]] = {}
    last_values: dict[str, dict[str, float]] = {}
    first_ts: dict[str, datetime] = {}
    last_ts: dict[str, datetime] = {}
    sensor_counts: dict[str, int] = {}
    global_start: datetime | None = None
    global_end: datetime | None = None
    record_count = 0

    for row in stream_csv_rows(csv_path):
        sid = row.get("sensor_id", "").strip()
        if not sid:
            continue

        ts_str = row.get("ts", "").strip()
        try:
            ts = parse_utc_timestamp(ts_str)
        except ValueError:
            continue

        record_count += 1
        sensor_counts[sid] = sensor_counts.get(sid, 0) + 1

        # Track first/last timestamps per sensor
        if sid not in first_ts or ts < first_ts[sid]:
            first_ts[sid] = ts
        if sid not in last_ts or ts > last_ts[sid]:
            last_ts[sid] = ts

        # Track global time range
        if global_start is None or ts < global_start:
            global_start = ts
        if global_end is None or ts > global_end:
            global_end = ts

        hour = ts.hour

        for col in metric_cols:
            val = try_parse_float(row.get(col, ""))
            if val is None:
                continue

            # Initialize accumulators
            if sid not in welford:
                welford[sid] = {}
                hourly[sid] = {}
                first_values[sid] = {}
                last_values[sid] = {}

            if col not in welford[sid]:
                welford[sid][col] = WelfordAccumulator()
                hourly[sid][col] = HourlyAccumulator()
                first_values[sid][col] = val

            welford[sid][col].update(val)
            hourly[sid][col].update(hour, val)
            last_values[sid][col] = val

    if global_start is None or global_end is None:
        raise CSVSchemaError("No valid timestamped records found in CSV.")

    # ── Build sensor entries ────────────────────────────────────────────
    time_origin = global_start
    time_origin_iso = format_utc_timestamp(time_origin)
    duration_s = datetime_to_offset_seconds(global_end, time_origin)

    sensor_entries: dict[str, SensorEntry] = {}
    for sid in sorted(welford.keys()):
        entry = SensorEntry(
            start_offset_s=datetime_to_offset_seconds(first_ts[sid], time_origin),
            end_offset_s=datetime_to_offset_seconds(last_ts[sid], time_origin),
            n=sensor_counts.get(sid, 0),
            metrics={},
        )
        for col in sorted(welford[sid].keys()):
            w = welford[sid][col]
            elapsed = datetime_to_offset_seconds(last_ts[sid], first_ts[sid])
            slope = 0.0
            if elapsed > 0 and w.n >= 2:
                slope = (last_values[sid][col] - first_values[sid][col]) / elapsed

            metric_entry = SensorMetricEntry(
                count=w.n,
                mean=w.mean,
                std=w.std,
                min=w.min_val,
                max=w.max_val,
                first=first_values[sid][col],
                last=last_values[sid][col],
                slope_per_second=slope,
                hourly_mean=hourly[sid][col].get_means(),
            )
            entry.metrics[col] = metric_entry

        sensor_entries[sid] = entry

    # ── Pass 2: Anomaly detection ───────────────────────────────────────
    # Use a min-heap to keep only top max_anomalies by z-score
    anomaly_heap: list[tuple[float, int, AnomalyEntry]] = []
    tie_counter = 0

    for row in stream_csv_rows(csv_path):
        sid = row.get("sensor_id", "").strip()
        if not sid or sid not in welford:
            continue

        ts_str = row.get("ts", "").strip()
        try:
            ts = parse_utc_timestamp(ts_str)
        except ValueError:
            continue

        t_offset = datetime_to_offset_seconds(ts, time_origin)

        for col in metric_cols:
            if col not in welford[sid]:
                continue
            val = try_parse_float(row.get(col, ""))
            if val is None:
                continue

            w = welford[sid][col]
            z = compute_z_score(val, w.mean, w.std)

            if z >= anomaly_z:
                entry = AnomalyEntry(
                    sensor_id=sid,
                    metric=col,
                    t_s=t_offset,
                    value=val,
                    z=z,
                )
                # Use min-heap: push negative z to get max-z behavior
                # But we want the top max_anomalies by z, so use min-heap on z
                if len(anomaly_heap) < max_anomalies:
                    heapq.heappush(anomaly_heap, (z, tie_counter, entry))
                    tie_counter += 1
                elif z > anomaly_heap[0][0]:
                    heapq.heapreplace(anomaly_heap, (z, tie_counter, entry))
                    tie_counter += 1

    # Sort anomalies by z-score descending
    anomaly_entries = [item[2] for item in sorted(anomaly_heap, key=lambda x: -x[0])]

    # ── Build container ─────────────────────────────────────────────────
    def build_full_container(
        sensors: dict[str, SensorEntry],
        anomalies: list[AnomalyEntry],
        metrics_list: list[str],
    ) -> dict[str, Any]:
        semantic_graph = build_semantic_graph(
            time_origin=time_origin_iso,
            duration_s=duration_s,
            sensor_count=len(sensors),
            record_count=record_count,
            metrics=metrics_list,
            sensors=sensors,
            anomalies=anomalies,
        )
        task_outputs = build_task_outputs(
            sensor_count=len(sensors),
            metric_count=len(metrics_list),
            record_count=record_count,
            duration_s=duration_s,
            anomaly_count=len(anomalies),
        )
        sparse_residual = build_sparse_residual(anomalies)
        procedural_seed = build_procedural_seed(seed=0)

        hdr = build_header(
            original_size_bytes=None,  # could be computed but not required
            original_record_count=record_count,
        )
        hdr["created_at"] = now_utc_iso()

        flags = {
            "lossless": FLAG_LOSSLESS,
            "bit_exact_reconstruction": FLAG_BIT_EXACT_RECONSTRUCTION,
            "semantic_equivalent": FLAG_SEMANTIC_EQUIVALENT,
        }

        semantic_checksum = build_semantic_checksum_field(
            contract=contract.to_dict(),
            semantic_graph=semantic_graph,
            task_outputs=task_outputs,
            flags=flags,
        )

        return {
            "header": hdr,
            "model_binding": build_model_binding(),
            "contract": contract.to_dict(),
            "semantic_graph": semantic_graph,
            "neural_latent": None,
            "procedural_seed": procedural_seed,
            "sparse_residual": sparse_residual,
            "task_outputs": task_outputs,
            "semantic_checksum": semantic_checksum,
        }

    container = build_full_container(sensor_entries, anomaly_entries, metric_cols)

    # ── Budget optimization ─────────────────────────────────────────────
    output_size = write_brk(container, output_path)
    is_within = within_budget(output_size, budget)

    if not is_within and strict_budget:
        # Apply progressive reduction
        output_size, container = _apply_budget_reduction(
            csv_path=csv_path,
            output_path=output_path,
            budget=budget,
            sensor_entries=sensor_entries,
            anomaly_entries=anomaly_entries,
            metric_cols=metric_cols,
            contract=contract,
            build_fn=build_full_container,
        )

    # Build report
    report = {
        "output_path": str(output_path),
        "output_size_bytes": output_size,
        "target_budget_bytes": budget,
        "within_budget": is_within,
        "compression_note": (
            "Within budget." if is_within
            else "Over budget. Increase budget or reduce data complexity."
        ),
        "lossless": False,
        "bit_exact_reconstruction": False,
        "semantic_equivalent": True,
        "record_count": record_count,
        "sensor_count": len(sensor_entries),
        "metric_count": len(metric_cols),
        "anomaly_count": len(anomaly_entries),
    }

    return report


def _apply_budget_reduction(
    csv_path: Path,
    output_path: Path,
    budget: int,
    sensor_entries: dict[str, SensorEntry],
    anomaly_entries: list[AnomalyEntry],
    metric_cols: list[str],
    contract: BRKContract,
    build_fn: Any,
) -> tuple[int, dict[str, Any]]:
    """Apply progressive budget reduction levels.

    Returns (output_size_bytes, container).
    Raises BudgetExceededError if all levels fail.
    """
    for level in range(BUDGET_LEVEL_FULL + 1, BUDGET_LEVEL_FAILURE + 1):
        reduced_sensors = _reduce_sensor_data(sensor_entries, level)
        reduced_anomalies = _reduce_anomalies(anomaly_entries, level)

        container = build_fn(
            sensors=reduced_sensors,
            anomalies=reduced_anomalies,
            metrics_list=metric_cols,
        )
        output_size = write_brk(container, output_path)

        if output_size <= budget:
            return output_size, container

    raise BudgetExceededError(
        actual_bytes=output_size,
        budget_bytes=budget,
    )


def _reduce_sensor_data(
    sensors: dict[str, SensorEntry], level: int
) -> dict[str, SensorEntry]:
    """Apply reduction level to sensor data."""
    import copy
    result = copy.deepcopy(sensors)

    if level >= BUDGET_LEVEL_ROUND_HOURLY:
        # Round hourly_mean more aggressively
        for entry in result.values():
            for metric in entry.metrics.values():
                metric.hourly_mean = [
                    round(v, 1) if v is not None else None
                    for v in metric.hourly_mean
                ]

    if level >= BUDGET_LEVEL_DROP_HOURLY:
        # Remove hourly_mean entirely
        for entry in result.values():
            for metric in entry.metrics.values():
                metric.hourly_mean = [None] * 24

    return result


def _reduce_anomalies(
    anomalies: list[AnomalyEntry], level: int
) -> list[AnomalyEntry]:
    """Apply reduction level to anomaly list."""
    if level >= BUDGET_LEVEL_HALF_ANOMALIES:
        anomalies = anomalies[: max(1, len(anomalies) // 2)]

    if level >= BUDGET_LEVEL_REDUCE_ANOMALIES:
        anomalies = anomalies[: max(1, len(anomalies) // 4)]

    return anomalies
