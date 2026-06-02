"""
Streaming CSV reader for BRK-Sensor Profile.

Supports two-pass reading of large CSV files without loading
the entire file into memory. Pass 1 collects statistics;
Pass 2 detects anomalies against those statistics.

Required columns: ts, sensor_id
Metric columns: any column that can be parsed as float.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from brk.constants import REQUIRED_COLUMNS
from brk.errors import CSVSchemaError


def detect_columns(header: list[str]) -> tuple[list[str], list[str]]:
    """Detect required and metric columns from a CSV header.

    Returns (required_columns_present, metric_columns).

    metric_columns are columns (other than ts and sensor_id) that
    can potentially be parsed as float.

    Raises CSVSchemaError if required columns are missing.
    """
    header_set = set(header)
    missing = [c for c in REQUIRED_COLUMNS if c not in header_set]
    if missing:
        raise CSVSchemaError(
            f"Missing required columns: {', '.join(missing)}. "
            f"Required: {', '.join(REQUIRED_COLUMNS)}"
        )

    metric_cols = [c for c in header if c not in REQUIRED_COLUMNS]
    return list(REQUIRED_COLUMNS), metric_cols


def stream_csv_rows(path: Path) -> Iterator[dict[str, str]]:
    """Stream CSV rows as dicts without loading the entire file.

    Yields one dict per row with column names as keys.
    Uses csv.DictReader for robust CSV parsing.
    """
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise CSVSchemaError("CSV file has no header row.")
        for row in reader:
            yield row


def try_parse_float(value: str) -> float | None:
    """Try to parse a string as float. Returns None on failure."""
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def is_metric_column(path: Path, col_name: str, sample_rows: int = 100) -> bool:
    """Determine if a column is a metric (numeric) column.

    Samples the first N rows and checks if the majority can be
    parsed as float.
    """
    count = 0
    parseable = 0
    for i, row in enumerate(stream_csv_rows(path)):
        if i >= sample_rows:
            break
        val = row.get(col_name, "")
        if val.strip() == "":
            continue
        count += 1
        if try_parse_float(val) is not None:
            parseable += 1

    if count == 0:
        return False
    return parseable / count > 0.5


def get_csv_header(path: Path) -> list[str]:
    """Read just the header row of a CSV file."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise CSVSchemaError("CSV file is empty.")
        return [h.strip() for h in header]


def detect_metric_columns(path: Path) -> list[str]:
    """Detect metric columns in a CSV file.

    Returns a list of column names that appear to contain numeric data.
    Excludes 'ts' and 'sensor_id'.
    """
    header = get_csv_header(path)
    _, candidate_metrics = detect_columns(header)
    metrics: list[str] = []
    for col in candidate_metrics:
        if is_metric_column(path, col):
            metrics.append(col)
    return metrics
