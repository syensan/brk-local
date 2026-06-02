"""
BRK-Sensor decompressor (reconstructor) implementation.

Reads a .brk container and reconstructs a semantic-equivalent CSV.
The reconstruction is NOT bit-exact — it generates an approximate
time series that satisfies the BRK contract.

IMPORTANT: BRK is NOT a universal lossless compressor.
The output is a semantic-equivalent reconstruction, not the original data.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from brk.constants import (
    DEFAULT_STEP_MINUTES,
    FLAG_BIT_EXACT_RECONSTRUCTION,
    FLAG_LOSSLESS,
    FLAG_SEMANTIC_EQUIVALENT,
)
from brk.container import read_brk, validate_container
from brk.contracts import validate_contract_dict, validate_flags_dict
from brk.errors import (
    InvalidBRKContainer,
    ReconstructionError,
    SemanticChecksumError,
)
from brk.checksum import compute_semantic_checksum
from brk.util.time import format_utc_timestamp, parse_utc_timestamp


def decompress_sensor(
    input_path: Path,
    output_path: Path,
    step_minutes: int = DEFAULT_STEP_MINUTES,
) -> dict[str, Any]:
    """Decompress (reconstruct) a semantic-equivalent CSV from a .brk container.

    Returns a metadata dict with reconstruction information.

    The output is NOT the original data — it is a semantic-equivalent
    reconstruction that satisfies the BRK contract.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    # ── Read and validate container ─────────────────────────────────────
    container = read_brk(input_path)

    # Validate safety invariants
    errors = validate_container(container)
    if errors:
        raise InvalidBRKContainer(
            "Container validation failed: " + "; ".join(errors)
        )

    # Verify semantic checksum
    header = container.get("header", {})
    flags = header.get("flags", {})
    contract = container.get("contract", {})
    semantic_graph = container.get("semantic_graph", {})
    task_outputs = container.get("task_outputs", {})
    sparse_residual = container.get("sparse_residual", {})
    semantic_checksum = container.get("semantic_checksum", {})

    expected_digest = compute_semantic_checksum(
        contract=contract,
        semantic_graph=semantic_graph,
        task_outputs=task_outputs,
        flags=flags,
    )
    actual_digest = semantic_checksum.get("digest", "")
    checksum_valid = actual_digest == expected_digest

    if not checksum_valid:
        raise SemanticChecksumError(
            expected=expected_digest,
            found=actual_digest,
        )

    # ── Reconstruct time series ─────────────────────────────────────────
    time_origin_str = semantic_graph.get("time_origin", "")
    sensors = semantic_graph.get("sensors", {})
    metrics = semantic_graph.get("metrics", [])
    anomalies_list = semantic_graph.get("anomalies", [])
    residual_anomalies = sparse_residual.get("anomalies", [])

    try:
        time_origin = parse_utc_timestamp(time_origin_str)
    except ValueError as e:
        raise ReconstructionError(f"Invalid time_origin: {e}") from e

    # Build anomaly lookup: (sensor_id, metric, t_s) -> value
    anomaly_map: dict[tuple[str, str, int], dict[str, Any]] = {}
    for a in residual_anomalies:
        key = (a.get("sensor_id", ""), a.get("metric", ""), a.get("t_s", 0))
        anomaly_map[key] = a
    # Also include semantic_graph anomalies
    for a in anomalies_list:
        key = (a.get("sensor_id", ""), a.get("metric", ""), a.get("t_s", 0))
        anomaly_map[key] = a

    # ── Write reconstructed CSV ─────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    step_td = timedelta(minutes=step_minutes)

    all_columns = ["ts", "sensor_id"] + list(metrics)
    row_count = 0

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()

        for sid in sorted(sensors.keys()):
            sensor = sensors[sid]
            sensor_metrics = sensor.get("metrics", {})
            start_offset_s = sensor.get("start_offset_s", 0)
            end_offset_s = sensor.get("end_offset_s", 0)

            current = time_origin + timedelta(seconds=start_offset_s)
            end = time_origin + timedelta(seconds=end_offset_s)

            while current <= end:
                elapsed_s = int((current - time_origin).total_seconds()) - start_offset_s
                ts_str = format_utc_timestamp(current)

                row: dict[str, str] = {
                    "ts": ts_str,
                    "sensor_id": sid,
                }

                for metric_name in metrics:
                    m = sensor_metrics.get(metric_name, {})
                    mean = m.get("mean", 0.0)
                    first = m.get("first", 0.0)
                    slope = m.get("slope_per_second", 0.0)
                    hourly_mean = m.get("hourly_mean", [None] * 24)

                    # Base trend: first + slope * elapsed
                    base = first + slope * elapsed_s

                    # Daily cycle component
                    current_hour = current.hour
                    hm = hourly_mean[current_hour] if current_hour < len(hourly_mean) else None
                    if hm is not None:
                        daily_component = hm - mean
                    else:
                        daily_component = 0.0

                    value = base + daily_component

                    # Check for anomaly injection
                    current_offset_s = int((current - time_origin).total_seconds())
                    anomaly_key = (sid, metric_name, current_offset_s)
                    if anomaly_key in anomaly_map:
                        value = anomaly_map[anomaly_key].get("value", value)

                    row[metric_name] = f"{value:.4f}"

                writer.writerow(row)
                row_count += 1
                current += step_td

    # ── Build reconstruction metadata ───────────────────────────────────
    contract_hash = compute_semantic_checksum(
        contract=contract,
        semantic_graph=semantic_graph,
        task_outputs=task_outputs,
        flags=flags,
    )

    metadata = {
        "reconstruction_type": "semantic_equivalent",
        "lossless": False,
        "bit_exact_reconstruction": False,
        "source_format": "brk",
        "profile": "BRK-Sensor",
        "model_id": "brk-sensor-analytic",
        "contract_hash": contract_hash,
        "semantic_checksum_valid": checksum_valid,
        "output_rows": row_count,
    }

    return metadata
