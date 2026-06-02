"""
Semantic checksum computation for BRK containers.

The semantic checksum is computed over:
  contract, semantic_graph, task_outputs, and header.flags

This is NOT a bit-exact checksum of source data.
It verifies that the semantic specification is intact.
"""

from __future__ import annotations

import hashlib

from brk.constants import FLAG_BIT_EXACT_RECONSTRUCTION, FLAG_LOSSLESS, FLAG_SEMANTIC_EQUIVALENT
from brk.util.json import canonical_encode


def compute_semantic_checksum(
    contract: dict,
    semantic_graph: dict,
    task_outputs: dict,
    flags: dict | None = None,
) -> str:
    """Compute the semantic checksum for a BRK container.

    The checksum covers contract, semantic_graph, task_outputs, and flags
    in canonical JSON form. Returns a hex digest string.

    This is NOT a bit-exact checksum of source data.
    """
    if flags is None:
        flags = {
            "lossless": FLAG_LOSSLESS,
            "bit_exact_reconstruction": FLAG_BIT_EXACT_RECONSTRUCTION,
            "semantic_equivalent": FLAG_SEMANTIC_EQUIVALENT,
        }
    payload = {
        "contract": contract,
        "semantic_graph": semantic_graph,
        "task_outputs": task_outputs,
        "flags": flags,
    }
    data = canonical_encode(payload)
    return hashlib.sha256(data).hexdigest()


def build_semantic_checksum_field(
    contract: dict,
    semantic_graph: dict,
    task_outputs: dict,
    flags: dict | None = None,
) -> dict:
    """Build the full semantic_checksum field for a BRK container.

    Returns a dict with algorithm, type, digest, and explanatory note.
    """
    digest = compute_semantic_checksum(contract, semantic_graph, task_outputs, flags)
    return {
        "algorithm": "sha256",
        "type": "semantic",
        "digest": digest,
        "note": (
            "Semantic checksum over contract, semantic_graph, task_outputs, "
            "and reconstruction flags. Not a bit-exact checksum of source data."
        ),
    }
