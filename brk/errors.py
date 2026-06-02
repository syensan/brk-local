"""
BRK Error Hierarchy.

All BRK-specific exceptions inherit from BRKError.
Exception messages are descriptive and user-friendly.

IMPORTANT: .brk is NOT a universal lossless compressor.
"""

from __future__ import annotations


class BRKError(Exception):
    """Base exception for all BRK errors."""


class InvalidBRKMagic(BRKError):
    """The file does not start with the expected BRK magic bytes."""

    def __init__(self, found: bytes | None = None) -> None:
        if found is not None:
            super().__init__(
                f"Invalid BRK magic bytes. Expected b'BRK1\\n', found {found!r}. "
                "This file is not a valid .brk container."
            )
        else:
            super().__init__(
                "Invalid BRK magic bytes. Expected b'BRK1\\n'. "
                "This file is not a valid .brk container."
            )


class UnsupportedCodec(BRKError):
    """The codec byte in the .brk file is not supported by this version."""

    def __init__(self, codec: int | None = None) -> None:
        if codec is not None:
            super().__init__(
                f"Unsupported payload codec: 0x{codec:02X}. "
                "This version of brk-local only supports codec 0x01 (zlib)."
            )
        else:
            super().__init__(
                "Unsupported payload codec. "
                "This version of brk-local only supports codec 0x01 (zlib)."
            )


class InvalidBRKContainer(BRKError):
    """The .brk container structure is invalid or incomplete."""

    def __init__(self, detail: str = "") -> None:
        msg = "Invalid BRK container structure."
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


class InvalidContract(BRKError):
    """The contract violates BRK safety invariants.

    Specifically, lossless must be false, bit_exact_reconstruction must be false,
    and semantic_equivalent must be true.
    """

    def __init__(self, detail: str = "") -> None:
        msg = (
            "Invalid BRK contract. BRK containers must have "
            "lossless=false, bit_exact_reconstruction=false, semantic_equivalent=true."
        )
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


class SemanticChecksumError(BRKError):
    """The semantic checksum does not match the recomputed value.

    This indicates the container has been corrupted or tampered with.
    Note: This is NOT a bit-exact checksum of source data.
    """

    def __init__(self, expected: str = "", found: str = "") -> None:
        msg = "Semantic checksum mismatch. The container may be corrupted."
        if expected and found:
            msg += f" Expected: {expected}, Found: {found}"
        super().__init__(msg)


class BudgetExceededError(BRKError):
    """The compressed output exceeds the target budget and strict mode is enabled."""

    def __init__(self, actual_bytes: int, budget_bytes: int) -> None:
        super().__init__(
            f"Budget exceeded in strict mode: output is {actual_bytes} bytes, "
            f"budget is {budget_bytes} bytes. "
            "Reduce sensor/metric count, anomalies, or increase the budget."
        )


class CSVSchemaError(BRKError):
    """The input CSV does not match the expected schema."""

    def __init__(self, detail: str = "") -> None:
        msg = "CSV schema error."
        if detail:
            msg += f" {detail}"
        super().__init__(msg)


class ReconstructionError(BRKError):
    """An error occurred during semantic reconstruction from .brk."""

    def __init__(self, detail: str = "") -> None:
        msg = "Reconstruction error."
        if detail:
            msg += f" {detail}"
        super().__init__(msg)
