"""
BRK Container Format Constants.

This module defines all magic bytes, codec identifiers, format versions,
and default values used throughout the BRK container system.

IMPORTANT: .brk is NOT a universal lossless compressor.
BRK does not break Shannon's theorem.
BRK stores a contract-bound semantic specification for acceptable reconstruction.
"""

# ── Magic & Format ──────────────────────────────────────────────────────────

MAGIC: bytes = b"BRK1\n"
MAGIC_STR: str = "BRK1"
FORMAT_VERSION: str = "0.1.0"
PROFILE_SENSOR: str = "BRK-Sensor"
CREATED_BY: str = "brk-local"

# ── Payload Codec ───────────────────────────────────────────────────────────

CODEC_ZLIB: int = 0x01

SUPPORTED_CODECS: frozenset[int] = frozenset({CODEC_ZLIB})

# ── Compression Defaults ────────────────────────────────────────────────────

ZLIB_LEVEL: int = 9
DEFAULT_BUDGET_BYTES: int = 1024
DEFAULT_MAX_ANOMALIES: int = 32
DEFAULT_ANOMALY_Z_THRESHOLD: float = 3.0
DEFAULT_STEP_MINUTES: int = 60

# ── Required CSV Columns ───────────────────────────────────────────────────

REQUIRED_COLUMNS: tuple[str, ...] = ("ts", "sensor_id")

# ── Safety Flags (MUST always be these values) ─────────────────────────────

FLAG_LOSSLESS: bool = False
FLAG_BIT_EXACT_RECONSTRUCTION: bool = False
FLAG_SEMANTIC_EQUIVALENT: bool = True

# ── Model Binding ───────────────────────────────────────────────────────────

MODEL_FAMILY: str = "BRK-Sensor-Analytic"
MODEL_ID: str = "brk-sensor-analytic"
MODEL_VERSION: str = "0.1.0"
DECODER_NAME: str = "trend_daily_cycle_anomaly_injection"

# ── Rounding ────────────────────────────────────────────────────────────────

FLOAT_PRECISION: int = 4

# ── Budget Reduction Levels ─────────────────────────────────────────────────

BUDGET_LEVEL_FULL: int = 0
BUDGET_LEVEL_ROUND_HOURLY: int = 1
BUDGET_LEVEL_DROP_HOURLY: int = 2
BUDGET_LEVEL_HALF_ANOMALIES: int = 3
BUDGET_LEVEL_REDUCE_ANOMALIES: int = 4
BUDGET_LEVEL_FAILURE: int = 5
