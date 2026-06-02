"""
BRK Container read/write operations.

A .brk file has the following binary structure:
  MAGIC (5 bytes: b"BRK1\\n") + CODEC_BYTE (1 byte) + zlib.compress(canonical_json)

IMPORTANT: .brk is NOT a universal lossless compressor.
BRK does not break Shannon's theorem.
BRK stores a contract-bound semantic specification for acceptable reconstruction.
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path
from typing import Any

from brk.constants import (
    CODEC_ZLIB,
    CREATED_BY,
    FLAG_BIT_EXACT_RECONSTRUCTION,
    FLAG_LOSSLESS,
    FLAG_SEMANTIC_EQUIVALENT,
    FORMAT_VERSION,
    MAGIC,
    MAGIC_STR,
    PROFILE_SENSOR,
    ZLIB_LEVEL,
)
from brk.contracts import validate_contract_dict, validate_flags_dict
from brk.errors import (
    InvalidBRKContainer,
    InvalidBRKMagic,
    SemanticChecksumError,
    UnsupportedCodec,
)
from brk.checksum import compute_semantic_checksum
from brk.util.json import canonical_encode


def build_header(
    original_size_bytes: int | None = None,
    original_record_count: int | None = None,
) -> dict[str, Any]:
    """Build the required header for a BRK container."""
    return {
        "magic": MAGIC_STR,
        "format_version": FORMAT_VERSION,
        "profile": PROFILE_SENSOR,
        "created_by": CREATED_BY,
        "created_at": "",  # filled by caller
        "flags": {
            "lossless": FLAG_LOSSLESS,
            "bit_exact_reconstruction": FLAG_BIT_EXACT_RECONSTRUCTION,
            "semantic_equivalent": FLAG_SEMANTIC_EQUIVALENT,
        },
        "original_size_bytes": original_size_bytes,
        "original_record_count": original_record_count,
    }


def build_model_binding() -> dict[str, Any]:
    """Build the required model_binding for BRK-Sensor-Analytic."""
    return {
        "model_family": "BRK-Sensor-Analytic",
        "model_id": "brk-sensor-analytic",
        "version": "0.1.0",
        "decoder": "trend_daily_cycle_anomaly_injection",
        "weights_hash": None,
        "note": "Analytic local model; no neural weights.",
    }


def write_brk(container: dict[str, Any], path: Path) -> int:
    """Write a BRK container dict to a .brk binary file.

    Returns the number of bytes written.

    The container dict must have all top-level fields populated.
    The payload is canonical JSON compressed with zlib level 9.
    """
    canonical_bytes = canonical_encode(container)
    compressed = zlib.compress(canonical_bytes, ZLIB_LEVEL)
    payload = MAGIC + bytes([CODEC_ZLIB]) + compressed

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(payload)

    return len(payload)


def read_brk(path: Path) -> dict[str, Any]:
    """Read a .brk binary file and return the container dict.

    Validates magic bytes, codec, and decompresses the payload.
    Raises InvalidBRKMagic, UnsupportedCodec, or InvalidBRKContainer.
    """
    with open(path, "rb") as f:
        data = f.read()

    if len(data) < 6:
        raise InvalidBRKContainer("File is too short to be a valid .brk container.")

    # Validate magic
    file_magic = data[:5]
    if file_magic != MAGIC:
        raise InvalidBRKMagic(found=file_magic)

    # Validate codec
    codec_byte = data[5]
    if codec_byte != CODEC_ZLIB:
        raise UnsupportedCodec(codec=codec_byte)

    # Decompress payload
    compressed_payload = data[6:]
    try:
        canonical_bytes = zlib.decompress(compressed_payload)
    except zlib.error as e:
        raise InvalidBRKContainer(f"zlib decompression failed: {e}") from e

    # Parse JSON
    try:
        container = json.loads(canonical_bytes)
    except json.JSONDecodeError as e:
        raise InvalidBRKContainer(f"JSON parse failed: {e}") from e

    return container


def validate_container(container: dict[str, Any]) -> list[str]:
    """Validate a BRK container structure and safety invariants.

    Returns a list of error messages. Empty list means valid.
    """
    errors: list[str] = []

    # Check required top-level fields
    required_fields = [
        "header", "model_binding", "contract", "semantic_graph",
        "neural_latent", "procedural_seed", "sparse_residual",
        "task_outputs", "semantic_checksum",
    ]
    for field_name in required_fields:
        if field_name not in container:
            errors.append(f"Missing required field: {field_name}")

    if errors:
        return errors

    # Validate header
    header = container.get("header", {})
    if header.get("magic") != MAGIC_STR:
        errors.append(f"header.magic must be {MAGIC_STR!r}, got {header.get('magic')!r}")
    if header.get("format_version") != FORMAT_VERSION:
        errors.append(f"header.format_version must be {FORMAT_VERSION!r}, got {header.get('format_version')!r}")
    if header.get("profile") != PROFILE_SENSOR:
        errors.append(f"header.profile must be {PROFILE_SENSOR!r}, got {header.get('profile')!r}")

    # Validate flags
    flags = header.get("flags", {})
    try:
        validate_flags_dict(flags)
    except Exception as e:
        errors.append(str(e))

    # Validate contract
    contract = container.get("contract", {})
    try:
        validate_contract_dict(contract)
    except Exception as e:
        errors.append(str(e))

    # Validate semantic checksum
    semantic_checksum = container.get("semantic_checksum", {})
    if semantic_checksum.get("algorithm") != "sha256":
        errors.append(f"semantic_checksum.algorithm must be 'sha256'")
    if semantic_checksum.get("type") != "semantic":
        errors.append("semantic_checksum.type must be 'semantic'")

    expected_digest = compute_semantic_checksum(
        contract=contract,
        semantic_graph=container.get("semantic_graph", {}),
        task_outputs=container.get("task_outputs", {}),
        flags=flags,
    )
    actual_digest = semantic_checksum.get("digest", "")
    if actual_digest != expected_digest:
        errors.append(
            f"Semantic checksum mismatch: expected {expected_digest}, got {actual_digest}"
        )

    return errors


def verify_brk(path: Path) -> tuple[bool, list[str]]:
    """Read and validate a .brk file.

    Returns (is_valid, error_messages).
    """
    try:
        container = read_brk(path)
    except (InvalidBRKMagic, UnsupportedCodec, InvalidBRKContainer) as e:
        return False, [str(e)]

    errors = validate_container(container)
    return len(errors) == 0, errors
