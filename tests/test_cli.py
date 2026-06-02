"""
Tests for BRK CLI commands.

Tests:
  - compress-sensor command
  - inspect command
  - verify command
  - decompress-sensor command
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from brk.cli import main


# ── Fixtures ────────────────────────────────────────────────────────────────

MINI_CSV = """\
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
"""


@pytest.fixture
def mini_csv_path(tmp_path: Path) -> Path:
    csv_path = tmp_path / "sensor.csv"
    csv_path.write_text(MINI_CSV, encoding="utf-8")
    return csv_path


@pytest.fixture
def brk_path(tmp_path: Path) -> Path:
    return tmp_path / "output.brk"


class TestCompressSensor:
    """Test the compress-sensor CLI command."""

    def test_compress_basic(self, mini_csv_path: Path, brk_path: Path) -> None:
        """Basic compress-sensor command succeeds."""
        ret = main([
            "compress-sensor",
            str(mini_csv_path),
            str(brk_path),
        ])
        assert ret == 0
        assert brk_path.exists()

    def test_compress_with_options(
        self, mini_csv_path: Path, brk_path: Path, tmp_path: Path
    ) -> None:
        """compress-sensor with all options works."""
        report_path = tmp_path / "report.json"
        ret = main([
            "compress-sensor",
            str(mini_csv_path),
            str(brk_path),
            "--budget", "2048",
            "--max-anomalies", "10",
            "--anomaly-z", "2.5",
            "--json-report", str(report_path),
        ])
        assert ret == 0
        assert brk_path.exists()
        assert report_path.exists()

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["lossless"] is False
        assert report["semantic_equivalent"] is True

    def test_compress_quiet(self, mini_csv_path: Path, brk_path: Path) -> None:
        """compress-sensor --quiet succeeds without error."""
        ret = main([
            "compress-sensor",
            str(mini_csv_path),
            str(brk_path),
            "--quiet",
        ])
        assert ret == 0


class TestInspect:
    """Test the inspect CLI command."""

    def test_inspect(self, mini_csv_path: Path, brk_path: Path) -> None:
        """inspect command shows container metadata."""
        main(["compress-sensor", str(mini_csv_path), str(brk_path)])
        ret = main(["inspect", str(brk_path)])
        assert ret == 0


class TestVerify:
    """Test the verify CLI command."""

    def test_verify_valid(self, mini_csv_path: Path, brk_path: Path) -> None:
        """verify command succeeds on a valid container."""
        main(["compress-sensor", str(mini_csv_path), str(brk_path)])
        ret = main(["verify", str(brk_path)])
        assert ret == 0

    def test_verify_invalid(self, tmp_path: Path) -> None:
        """verify command fails on an invalid file."""
        bad_path = tmp_path / "bad.brk"
        bad_path.write_bytes(b"NOTABRK1\n!!")
        ret = main(["verify", str(bad_path)])
        assert ret != 0


class TestDecompressSensor:
    """Test the decompress-sensor CLI command."""

    def test_decompress_basic(
        self, mini_csv_path: Path, brk_path: Path, tmp_path: Path
    ) -> None:
        """Basic decompress-sensor command succeeds."""
        csv_out = tmp_path / "reconstructed.csv"

        main(["compress-sensor", str(mini_csv_path), str(brk_path)])
        ret = main([
            "decompress-sensor",
            str(brk_path),
            str(csv_out),
        ])
        assert ret == 0
        assert csv_out.exists()

    def test_decompress_with_metadata(
        self, mini_csv_path: Path, brk_path: Path, tmp_path: Path
    ) -> None:
        """decompress-sensor with --metadata-json produces metadata file."""
        csv_out = tmp_path / "reconstructed.csv"
        meta_path = tmp_path / "meta.json"

        main(["compress-sensor", str(mini_csv_path), str(brk_path)])
        ret = main([
            "decompress-sensor",
            str(brk_path),
            str(csv_out),
            "--metadata-json", str(meta_path),
        ])
        assert ret == 0
        assert meta_path.exists()

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["reconstruction_type"] == "semantic_equivalent"
        assert meta["lossless"] is False
        assert meta["bit_exact_reconstruction"] is False

    def test_decompress_with_step(
        self, mini_csv_path: Path, brk_path: Path, tmp_path: Path
    ) -> None:
        """decompress-sensor with --step-minutes produces output."""
        csv_out = tmp_path / "reconstructed.csv"

        main(["compress-sensor", str(mini_csv_path), str(brk_path)])
        ret = main([
            "decompress-sensor",
            str(brk_path),
            str(csv_out),
            "--step-minutes", "60",
        ])
        assert ret == 0


class TestNoCommand:
    """Test CLI with no command."""

    def test_no_command_returns_nonzero(self) -> None:
        """Running with no command returns non-zero exit code."""
        ret = main([])
        assert ret != 0
