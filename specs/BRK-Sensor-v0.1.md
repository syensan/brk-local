# BRK-Sensor Profile Specification v0.1

## Overview

BRK-Sensor is the first profile for the BRK container format, designed for agricultural and IoT sensor time-series data. It compresses CSV data into a semantic specification that preserves statistical properties, trends, daily cycles, and anomalies — but **NOT** the original data bit-for-bit.

**This is NOT a lossless compressor.**
**BRK does not break Shannon's theorem.**

## Target Data

- **Domain**: Agricultural sensors, IoT environmental sensors
- **Format**: CSV (primary), JSON (secondary)
- **Scale**: Up to 1GB+ CSV files (streaming processing, no full in-memory load)

## CSV Schema

### Required Columns

| Column     | Type   | Description                          |
|------------|--------|--------------------------------------|
| `ts`       | string | ISO-8601 UTC timestamp               |
| `sensor_id`| string | Unique sensor identifier             |

### Metric Columns

Any column other than `ts` and `sensor_id` that can be parsed as `float` is treated as a metric column.

Example metrics:
- `temperature` (°C)
- `humidity` (%)
- `soil_moisture` (%)

### Metric Detection

Metric columns are detected by sampling the first 100 rows and checking whether the majority of non-empty values can be parsed as float.

### Example CSV

```csv
ts,sensor_id,temperature,humidity,soil_moisture
2026-01-01T00:00:00Z,field-01,20.1,61.2,33.4
2026-01-01T01:00:00Z,field-01,19.8,63.0,33.1
2026-01-01T02:00:00Z,field-01,50.0,62.8,12.0
2026-01-01T03:00:00Z,field-01,20.4,60.9,33.6
2026-01-01T04:00:00Z,field-01,20.2,61.1,33.2
2026-01-01T00:00:00Z,field-02,18.2,70.1,40.2
2026-01-01T01:00:00Z,field-02,18.1,70.5,40.0
2026-01-01T02:00:00Z,field-02,18.3,70.0,39.9
2026-01-01T03:00:00Z,field-02,18.2,69.8,40.1
```

## Compression Contract

The default contract for BRK-Sensor v0.1:

```json
{
  "mode": "brk-task",
  "domain": "agricultural_sensor",
  "lossless": false,
  "bit_exact_reconstruction": false,
  "semantic_equivalent": true,
  "tasks": [
    "daily_statistics",
    "trend_reconstruction",
    "anomaly_preservation"
  ],
  "tolerances": {
    "temperature_rmse_celsius": 0.5,
    "humidity_rmse_percent": 3.0,
    "soil_moisture_rmse_percent": 2.0,
    "anomaly_time_error_minutes": 10
  },
  "hard_constraints": [
    "preserve_sensor_count",
    "preserve_detected_anomalies"
  ]
}
```

### Tasks

1. **daily_statistics**: Per-sensor, per-metric mean, std, min, max are preserved.
2. **trend_reconstruction**: Linear trend (first/last/slope) and daily cycle (hourly means) are preserved.
3. **anomaly_preservation**: Top z-score anomalies are preserved as sparse residuals.

### Tolerances

The tolerances define acceptable RMSE and timing errors for the reconstructed data. These are *targets*, not guarantees.

### Hard Constraints

These MUST be satisfied:
- `preserve_sensor_count`: The number of distinct sensors is preserved.
- `preserve_detected_anomalies`: Detected anomalies are included in the sparse residual.

## Semantic Graph Schema

```json
{
  "type": "sensor_timeseries_graph",
  "time_origin": "<ISO8601 UTC>",
  "duration_s": <int>,
  "sensor_count": <int>,
  "record_count": <int>,
  "metrics": ["temperature", ...],
  "sensors": {
    "<sensor_id>": {
      "start_offset_s": <int>,
      "end_offset_s": <int>,
      "n": <int>,
      "metrics": {
        "<metric>": {
          "count": <int>,
          "mean": <float>,
          "std": <float>,
          "min": <float>,
          "max": <float>,
          "first": <float>,
          "last": <float>,
          "slope_per_second": <float>,
          "hourly_mean": [24 values or nulls]
        }
      }
    }
  },
  "anomalies": [
    {
      "sensor_id": "...",
      "metric": "...",
      "t_s": <offset seconds from time_origin>,
      "value": <float>,
      "z": <float>
    }
  ]
}
```

### Field Descriptions

- `time_origin`: The earliest timestamp in the dataset (UTC).
- `duration_s`: Duration in seconds from time_origin to the latest timestamp.
- `start_offset_s` / `end_offset_s`: Offset in seconds from time_origin for this sensor's time range.
- `slope_per_second`: Linear slope from first to last value, in units/second.
- `hourly_mean`: Array of 24 values (one per hour 0-23), or `null` if no data for that hour.
- `anomalies.t_s`: Offset in seconds from time_origin.

## Anomaly Residual Schema

Anomalies are stored in both `semantic_graph.anomalies` and `sparse_residual.anomalies`:

```json
{
  "anomalies": [
    {
      "sensor_id": "...",
      "metric": "...",
      "t_s": <int>,
      "value": <float>,
      "z": <float>
    }
  ]
}
```

Anomalies are detected using z-score with a configurable threshold (default: 3.0). Only the top `max_anomalies` (default: 32) by z-score are kept, using a min-heap to avoid loading all anomalies into memory.

## Reconstruction Algorithm

The decoder `trend_daily_cycle_anomaly_injection` reconstructs time series as:

1. For each sensor, generate timestamps from `start_offset_s` to `end_offset_s` at `step_minutes` intervals.
2. For each metric at each timestamp:
   - **Base trend**: `first + slope_per_second * elapsed_seconds`
   - **Daily cycle**: `hourly_mean[current_hour] - mean` (if hourly_mean is available, else 0)
   - **Value**: `base + daily_component`
3. **Anomaly injection**: If an anomaly exists for `(sensor_id, metric, t_s)`, replace the value with the anomaly's `value`.

### Output Format

- Reconstructed CSV with same columns as input
- No comment lines in output (pure CSV)
- Reconstruction metadata available via `--metadata-json`

## Verification

Verification checks:
1. Container structure validity (all required fields present)
2. Safety invariant compliance (lossless=false, etc.)
3. Semantic checksum integrity
4. Profile compatibility

## Limitations

1. **NOT lossless**: Original data cannot be recovered bit-for-bit.
2. **Budget-dependent**: The 1024-byte target budget depends on data complexity. Complex data with many sensors/metrics/anomalies may exceed the budget.
3. **Approximate**: Reconstructed values are approximations based on linear trend + daily cycle + anomaly injection.
4. **No neural model**: v0.1 uses an analytic model only. Future versions may support neural generative models.
5. **Timestamp regularity**: Reconstructed timestamps are at regular intervals, which may not match the original irregular timestamps.
6. **Single domain**: v0.1 only supports agricultural/IoT sensor data.

## Examples

### Compress

```bash
brk compress-sensor examples/sample_sensor.csv output.brk
```

### Inspect

```bash
brk inspect output.brk
```

### Verify

```bash
brk verify output.brk
```

### Decompress

```bash
brk decompress-sensor output.brk reconstructed.csv --step-minutes 60
```
