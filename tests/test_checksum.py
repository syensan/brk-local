"""
Tests for BRK semantic checksum.

Tests:
  - Checksum is stable across repeated computations
  - Container modification causes checksum mismatch
"""

from __future__ import annotations

from pathlib import Path

import pytest

from brk.checksum import compute_semantic_checksum, build_semantic_checksum_field
from brk.contracts import BRKContract
from brk.container import build_header, build_model_binding, write_brk, read_brk, validate_container
from brk.constants import MAGIC_STR


def _make_test_data() -> tuple[dict, dict, dict, dict]:
    """Create test data for checksum tests."""
    contract = BRKContract()
    contract_dict = contract.to_dict()
    semantic_graph = {
        "type": "sensor_timeseries_graph",
        "time_origin": "2026-01-01T00:00:00Z",
        "duration_s": 7200,
        "sensor_count": 2,
        "record_count": 100,
        "metrics": ["temperature", "humidity"],
        "sensors": {},
        "anomalies": [],
    }
    task_outputs = {
        "sensor_count": 2,
        "metric_count": 2,
        "record_count": 100,
        "duration_s": 7200,
        "anomaly_count": 0,
    }
    flags = {
        "lossless": False,
        "bit_exact_reconstruction": False,
        "semantic_equivalent": True,
    }
    return contract_dict, semantic_graph, task_outputs, flags


class TestChecksumStability:
    """Test that semantic checksums are deterministic."""

    def test_same_input_same_digest(self) -> None:
        """Computing the checksum twice with the same input gives the same digest."""
        contract_dict, sg, to, flags = _make_test_data()

        digest1 = compute_semantic_checksum(contract_dict, sg, to, flags)
        digest2 = compute_semantic_checksum(contract_dict, sg, to, flags)

        assert digest1 == digest2
        assert len(digest1) == 64  # SHA-256 hex digest length

    def test_different_input_different_digest(self) -> None:
        """Changing the input changes the checksum."""
        contract_dict, sg, to, flags = _make_test_data()

        digest1 = compute_semantic_checksum(contract_dict, sg, to, flags)

        # Modify the data
        sg_modified = dict(sg)
        sg_modified["sensor_count"] = 99

        digest2 = compute_semantic_checksum(contract_dict, sg_modified, to, flags)

        assert digest1 != digest2

    def test_build_semantic_checksum_field(self) -> None:
        """build_semantic_checksum_field returns a properly structured dict."""
        contract_dict, sg, to, flags = _make_test_data()

        field = build_semantic_checksum_field(contract_dict, sg, to, flags)

        assert field["algorithm"] == "sha256"
        assert field["type"] == "semantic"
        assert len(field["digest"]) == 64
        assert "Not a bit-exact checksum" in field["note"]


class TestChecksumTamperDetection:
    """Test that container tampering is detected via checksum mismatch."""

    def test_valid_container_passes_checksum(self, tmp_path: Path) -> None:
        """A valid container passes checksum validation."""
        contract = BRKContract()
        contract_dict = contract.to_dict()
        header = build_header(original_record_count=10)
        header["created_at"] = "2026-01-01T00:00:00Z"
        flags = header["flags"]

        sg = {
            "type": "sensor_timeseries_graph",
            "time_origin": "2026-01-01T00:00:00Z",
            "duration_s": 3600,
            "sensor_count": 1,
            "record_count": 10,
            "metrics": ["temperature"],
            "sensors": {},
            "anomalies": [],
        }
        to = {
            "sensor_count": 1,
            "metric_count": 1,
            "record_count": 10,
            "duration_s": 3600,
            "anomaly_count": 0,
        }
        sc = build_semantic_checksum_field(contract_dict, sg, to, flags)

        container = {
            "header": header,
            "model_binding": build_model_binding(),
            "contract": contract_dict,
            "semantic_graph": sg,
            "neural_latent": None,
            "procedural_seed": {"generator": "deterministic_sensor_timeseries_reconstructor", "seed": 0},
            "sparse_residual": {"anomalies": []},
            "task_outputs": to,
            "semantic_checksum": sc,
        }

        brk_path = tmp_path / "valid.brk"
        write_brk(container, brk_path)

        errors = validate_container(container)
        assert len(errors) == 0

    def test_tampered_container_fails_checksum(self, tmp_path: Path) -> None:
        """Modifying the semantic_graph after checksum computation causes validation failure."""
        contract = BRKContract()
        contract_dict = contract.to_dict()
        header = build_header(original_record_count=10)
        header["created_at"] = "2026-01-01T00:00:00Z"
        flags = header["flags"]

        sg = {
            "type": "sensor_timeseries_graph",
            "time_origin": "2026-01-01T00:00:00Z",
            "duration_s": 3600,
            "sensor_count": 1,
            "record_count": 10,
            "metrics": ["temperature"],
            "sensors": {},
            "anomalies": [],
        }
        to = {
            "sensor_count": 1,
            "metric_count": 1,
            "record_count": 10,
            "duration_s": 3600,
            "anomaly_count": 0,
        }
        sc = build_semantic_checksum_field(contract_dict, sg, to, flags)

        # Tamper: change sensor_count in semantic_graph AFTER computing checksum
        sg_tampered = dict(sg)
        sg_tampered["sensor_count"] = 99

        container = {
            "header": header,
            "model_binding": build_model_binding(),
            "contract": contract_dict,
            "semantic_graph": sg_tampered,  # tampered!
            "neural_latent": None,
            "procedural_seed": {"generator": "deterministic_sensor_timeseries_reconstructor", "seed": 0},
            "sparse_residual": {"anomalies": []},
            "task_outputs": to,
            "semantic_checksum": sc,  # checksum computed with original sg
        }

        errors = validate_container(container)
        assert len(errors) > 0
        assert any("checksum mismatch" in e.lower() for e in errors)
