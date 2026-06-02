"""
Tests for BRK container read/write operations.

Tests:
  - BRK write/read roundtrip
  - Magic mismatch rejection
  - Unsupported codec rejection
"""

from __future__ import annotations

import json
import zlib
from pathlib import Path

import pytest

from brk.constants import (
    CODEC_ZLIB,
    FLAG_BIT_EXACT_RECONSTRUCTION,
    FLAG_LOSSLESS,
    FLAG_SEMANTIC_EQUIVALENT,
    MAGIC,
    MAGIC_STR,
)
from brk.container import build_header, build_model_binding, read_brk, write_brk
from brk.checksum import build_semantic_checksum_field
from brk.contracts import BRKContract
from brk.errors import InvalidBRKMagic, UnsupportedCodec, InvalidBRKContainer
from brk.util.json import canonical_encode


def _make_valid_container() -> dict:
    """Create a minimal valid BRK container for testing."""
    contract = BRKContract()
    contract_dict = contract.to_dict()
    header = build_header(original_size_bytes=1000, original_record_count=50)
    header["created_at"] = "2026-01-01T00:00:00Z"
    flags = header["flags"]

    semantic_graph = {
        "type": "sensor_timeseries_graph",
        "time_origin": "2026-01-01T00:00:00Z",
        "duration_s": 3600,
        "sensor_count": 1,
        "record_count": 50,
        "metrics": ["temperature"],
        "sensors": {
            "field-01": {
                "start_offset_s": 0,
                "end_offset_s": 3600,
                "n": 50,
                "metrics": {
                    "temperature": {
                        "count": 50,
                        "mean": 20.0,
                        "std": 1.0,
                        "min": 18.0,
                        "max": 22.0,
                        "first": 20.1,
                        "last": 19.9,
                        "slope_per_second": -0.0001,
                        "hourly_mean": [20.0] * 24,
                    }
                },
            }
        },
        "anomalies": [],
    }
    task_outputs = {
        "sensor_count": 1,
        "metric_count": 1,
        "record_count": 50,
        "duration_s": 3600,
        "anomaly_count": 0,
    }
    semantic_checksum = build_semantic_checksum_field(
        contract=contract_dict,
        semantic_graph=semantic_graph,
        task_outputs=task_outputs,
        flags=flags,
    )

    return {
        "header": header,
        "model_binding": build_model_binding(),
        "contract": contract_dict,
        "semantic_graph": semantic_graph,
        "neural_latent": None,
        "procedural_seed": {"generator": "deterministic_sensor_timeseries_reconstructor", "seed": 0},
        "sparse_residual": {"anomalies": []},
        "task_outputs": task_outputs,
        "semantic_checksum": semantic_checksum,
    }


class TestBRKWriteReadRoundtrip:
    """Test that writing and reading a .brk container preserves data."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Write a valid container, read it back, verify fields match."""
        container = _make_valid_container()
        brk_path = tmp_path / "test.brk"

        size = write_brk(container, brk_path)
        assert size > 0
        assert brk_path.exists()

        loaded = read_brk(brk_path)

        # Verify key fields survived roundtrip
        assert loaded["header"]["magic"] == MAGIC_STR
        assert loaded["header"]["format_version"] == "0.1.0"
        assert loaded["header"]["profile"] == "BRK-Sensor"
        assert loaded["header"]["flags"]["lossless"] is False
        assert loaded["header"]["flags"]["bit_exact_reconstruction"] is False
        assert loaded["header"]["flags"]["semantic_equivalent"] is True
        assert loaded["contract"]["lossless"] is False
        assert loaded["contract"]["semantic_equivalent"] is True

    def test_roundtrip_preserves_semantic_graph(self, tmp_path: Path) -> None:
        """Verify semantic_graph survives roundtrip."""
        container = _make_valid_container()
        brk_path = tmp_path / "test.brk"

        write_brk(container, brk_path)
        loaded = read_brk(brk_path)

        assert loaded["semantic_graph"]["sensor_count"] == 1
        assert "field-01" in loaded["semantic_graph"]["sensors"]
        assert loaded["semantic_graph"]["metrics"] == ["temperature"]


class TestMagicMismatch:
    """Test that files with wrong magic bytes are rejected."""

    def test_invalid_magic(self, tmp_path: Path) -> None:
        """A file with wrong magic bytes raises InvalidBRKMagic."""
        bad_path = tmp_path / "bad.brk"
        with open(bad_path, "wb") as f:
            f.write(b"XXXXX" + bytes([0x01]) + b"dummy data")

        with pytest.raises(InvalidBRKMagic):
            read_brk(bad_path)

    def test_empty_file(self, tmp_path: Path) -> None:
        """An empty file raises InvalidBRKContainer."""
        bad_path = tmp_path / "empty.brk"
        bad_path.write_bytes(b"")

        with pytest.raises(InvalidBRKContainer):
            read_brk(bad_path)

    def test_truncated_file(self, tmp_path: Path) -> None:
        """A file that's too short raises InvalidBRKContainer."""
        bad_path = tmp_path / "trunc.brk"
        bad_path.write_bytes(b"BRK")

        with pytest.raises(InvalidBRKContainer):
            read_brk(bad_path)


class TestUnsupportedCodec:
    """Test that unsupported codec bytes are rejected."""

    def test_unknown_codec(self, tmp_path: Path) -> None:
        """A file with codec byte 0xFF raises UnsupportedCodec."""
        bad_path = tmp_path / "bad_codec.brk"
        with open(bad_path, "wb") as f:
            f.write(MAGIC + bytes([0xFF]) + b"dummy data")

        with pytest.raises(UnsupportedCodec):
            read_brk(bad_path)

    def test_valid_codec(self, tmp_path: Path) -> None:
        """Codec byte 0x01 (zlib) is accepted."""
        container = _make_valid_container()
        brk_path = tmp_path / "valid_codec.brk"
        write_brk(container, brk_path)

        # Should not raise
        loaded = read_brk(brk_path)
        assert loaded["header"]["magic"] == MAGIC_STR
