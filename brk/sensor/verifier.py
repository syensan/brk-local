"""
BRK-Sensor container verifier.

Validates the structural integrity, safety invariants,
and semantic checksum of a .brk file.

IMPORTANT: BRK is NOT a universal lossless compressor.
Verification checks the semantic specification, not bit-exact data integrity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from brk.container import read_brk, validate_container
from brk.errors import InvalidBRKContainer


def verify_sensor_brk(path: Path) -> dict[str, Any]:
    """Verify a BRK-Sensor .brk container.

    Checks:
      - Container structure
      - Safety flags (lossless=false, etc.)
      - Contract invariants
      - Semantic checksum

    Returns a dict with:
      - valid: bool
      - errors: list of error strings
      - profile: str or None
      - model_id: str or None
    """
    path = Path(path)

    # Try to read the container
    try:
        container = read_brk(path)
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "profile": None,
            "model_id": None,
        }

    # Validate structure and invariants
    errors = validate_container(container)

    profile = container.get("header", {}).get("profile")
    model_id = container.get("model_binding", {}).get("model_id")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "profile": profile,
        "model_id": model_id,
    }
