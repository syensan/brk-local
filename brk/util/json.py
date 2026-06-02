"""
JSON canonical serialization utilities for BRK containers.

All JSON serialization in BRK MUST go through these functions to ensure
deterministic, canonical output for checksum stability.
"""

from __future__ import annotations

import json
from typing import Any


def canonical_dumps(obj: Any) -> str:
    """Serialize an object to canonical JSON string.

    Canonical form: sorted keys, no extra whitespace, no ASCII escaping.
    This ensures deterministic output for checksum computation.
    """
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_encode(obj: Any) -> bytes:
    """Serialize an object to canonical UTF-8 JSON bytes.

    This is the form used for:
    - Payload compression in .brk files
    - Semantic checksum computation
    """
    return canonical_dumps(obj).encode("utf-8")


def canonical_decode(data: bytes) -> Any:
    """Decode canonical JSON bytes back to a Python object."""
    return json.loads(data)
