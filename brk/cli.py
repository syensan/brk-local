"""
CLI for BRK - Breakthrough Container.

Commands:
  compress-sensor   Compress a sensor CSV into a .brk container
  decompress-sensor Reconstruct a semantic-equivalent CSV from .brk
  inspect           Inspect a .brk container's metadata
  verify            Verify a .brk container's integrity

IMPORTANT: BRK is NOT a universal lossless compressor.
BRK stores a contract-bound semantic specification for acceptable reconstruction.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from brk import __version__
from brk.container import read_brk
from brk.sensor.compressor import compress_sensor
from brk.sensor.decompressor import decompress_sensor
from brk.sensor.verifier import verify_sensor_brk
from brk.util.size import format_size


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point. Returns 0 on success, non-zero on failure."""
    parser = argparse.ArgumentParser(
        prog="brk",
        description=(
            "BRK - Breakthrough Container. "
            "A semantic/task-oriented reconstruction container format. "
            "BRK is NOT a universal lossless compressor. "
            "BRK does not break Shannon's theorem."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"brk {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command")

    # ── compress-sensor ─────────────────────────────────────────────────
    comp = subparsers.add_parser(
        "compress-sensor",
        help="Compress a sensor CSV into a .brk container",
    )
    comp.add_argument("csv_path", type=Path, help="Path to input CSV file")
    comp.add_argument("output_path", type=Path, help="Path to output .brk file")
    comp.add_argument(
        "--contract", type=Path, default=None,
        help="Path to optional contract JSON file",
    )
    comp.add_argument(
        "--budget", type=int, default=1024,
        help="Target budget in bytes (default: 1024)",
    )
    comp.add_argument(
        "--max-anomalies", type=int, default=32,
        help="Maximum anomalies to preserve (default: 32)",
    )
    comp.add_argument(
        "--anomaly-z", type=float, default=3.0,
        help="Z-score threshold for anomaly detection (default: 3.0)",
    )
    comp.add_argument(
        "--strict-budget", action="store_true",
        help="Fail if output exceeds budget after reduction attempts",
    )
    comp.add_argument(
        "--quiet", action="store_true",
        help="Suppress informational output",
    )
    comp.add_argument(
        "--json-report", type=Path, default=None,
        help="Write compression report as JSON to this path",
    )

    # ── decompress-sensor ───────────────────────────────────────────────
    decomp = subparsers.add_parser(
        "decompress-sensor",
        help="Reconstruct a semantic-equivalent CSV from .brk",
    )
    decomp.add_argument("input_path", type=Path, help="Path to input .brk file")
    decomp.add_argument("output_path", type=Path, help="Path to output CSV file")
    decomp.add_argument(
        "--step-minutes", type=int, default=60,
        help="Time step in minutes for reconstruction (default: 60)",
    )
    decomp.add_argument(
        "--metadata-json", type=Path, default=None,
        help="Write reconstruction metadata as JSON to this path",
    )
    decomp.add_argument(
        "--quiet", action="store_true",
        help="Suppress informational output",
    )

    # ── inspect ─────────────────────────────────────────────────────────
    insp = subparsers.add_parser(
        "inspect",
        help="Inspect a .brk container's metadata",
    )
    insp.add_argument("input_path", type=Path, help="Path to .brk file")

    # ── verify ──────────────────────────────────────────────────────────
    ver = subparsers.add_parser(
        "verify",
        help="Verify a .brk container's integrity",
    )
    ver.add_argument("input_path", type=Path, help="Path to .brk file")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        if args.command == "compress-sensor":
            return _cmd_compress_sensor(args)
        elif args.command == "decompress-sensor":
            return _cmd_decompress_sensor(args)
        elif args.command == "inspect":
            return _cmd_inspect(args)
        elif args.command == "verify":
            return _cmd_verify(args)
        else:
            parser.print_help()
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_compress_sensor(args: argparse.Namespace) -> int:
    """Execute the compress-sensor command."""
    contract_json = None
    if args.contract is not None:
        with open(args.contract, "r", encoding="utf-8") as f:
            contract_json = json.load(f)

    report = compress_sensor(
        csv_path=args.csv_path,
        output_path=args.output_path,
        contract_json=contract_json,
        budget=args.budget,
        max_anomalies=args.max_anomalies,
        anomaly_z=args.anomaly_z,
        strict_budget=args.strict_budget,
    )

    # Save JSON report if requested
    if args.json_report is not None:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    if not args.quiet:
        print("BRK-Sensor compression complete.")
        print(f"Output: {report['output_path']}")
        print(f"Output size: {report['output_size_bytes']} bytes")
        print(f"Target budget: {report['target_budget_bytes']} bytes")
        print(f"Within budget: {'true' if report['within_budget'] else 'false'}")
        print(f"Lossless: false")
        print(f"Bit-exact reconstruction: false")
        print(f"Semantic equivalent: true")

        if not report["within_budget"]:
            print(
                f"Warning: Output exceeds target budget of {report['target_budget_bytes']} bytes. "
                "Increase budget or reduce data complexity.",
            )

    return 0


def _cmd_decompress_sensor(args: argparse.Namespace) -> int:
    """Execute the decompress-sensor command."""
    metadata = decompress_sensor(
        input_path=args.input_path,
        output_path=args.output_path,
        step_minutes=args.step_minutes,
    )

    # Save metadata JSON if requested
    if args.metadata_json is not None:
        args.metadata_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.metadata_json, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    if not args.quiet:
        print("BRK-Sensor reconstruction complete.")
        print(f"Output: {args.output_path}")
        print(f"Reconstruction type: semantic_equivalent")
        print(f"Lossless: false")
        print(f"Bit-exact reconstruction: false")
        print(f"Semantic checksum valid: {'true' if metadata['semantic_checksum_valid'] else 'false'}")

    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    """Execute the inspect command."""
    container = read_brk(args.input_path)

    header = container.get("header", {})
    model_binding = container.get("model_binding", {})
    contract = container.get("contract", {})
    semantic_graph = container.get("semantic_graph", {})
    task_outputs = container.get("task_outputs", {})
    file_size = args.input_path.stat().st_size

    print("=== BRK Container Inspection ===")
    print()
    print("Header:")
    print(f"  Magic: {header.get('magic', 'N/A')}")
    print(f"  Format version: {header.get('format_version', 'N/A')}")
    print(f"  Profile: {header.get('profile', 'N/A')}")
    print(f"  Created by: {header.get('created_by', 'N/A')}")
    print(f"  Created at: {header.get('created_at', 'N/A')}")
    print(f"  Original size: {header.get('original_size_bytes', 'N/A')} bytes")
    print(f"  Original record count: {header.get('original_record_count', 'N/A')}")
    print()
    print("Flags:")
    flags = header.get("flags", {})
    print(f"  Lossless: {flags.get('lossless', 'N/A')} (must be false)")
    print(f"  Bit-exact reconstruction: {flags.get('bit_exact_reconstruction', 'N/A')} (must be false)")
    print(f"  Semantic equivalent: {flags.get('semantic_equivalent', 'N/A')} (must be true)")
    print()
    print("Model Binding:")
    print(f"  Model family: {model_binding.get('model_family', 'N/A')}")
    print(f"  Model ID: {model_binding.get('model_id', 'N/A')}")
    print(f"  Version: {model_binding.get('version', 'N/A')}")
    print(f"  Decoder: {model_binding.get('decoder', 'N/A')}")
    print()
    print("Contract Summary:")
    print(f"  Mode: {contract.get('mode', 'N/A')}")
    print(f"  Domain: {contract.get('domain', 'N/A')}")
    print(f"  Lossless: {contract.get('lossless', 'N/A')} (must be false)")
    print(f"  Bit-exact reconstruction: {contract.get('bit_exact_reconstruction', 'N/A')} (must be false)")
    print(f"  Semantic equivalent: {contract.get('semantic_equivalent', 'N/A')} (must be true)")
    print(f"  Tasks: {', '.join(contract.get('tasks', []))}")
    print()
    print("Data Summary:")
    print(f"  Sensor count: {semantic_graph.get('sensor_count', 'N/A')}")
    print(f"  Metric count: {len(semantic_graph.get('metrics', []))}")
    print(f"  Metrics: {', '.join(semantic_graph.get('metrics', []))}")
    print(f"  Record count: {semantic_graph.get('record_count', 'N/A')}")
    print(f"  Duration: {semantic_graph.get('duration_s', 'N/A')} seconds")
    print(f"  Anomaly count: {task_outputs.get('anomaly_count', 'N/A')}")
    print()
    print(f"File size: {file_size} bytes ({format_size(file_size)})")
    print()
    print("NOTE: This container does NOT provide bit-exact reconstruction.")
    print("      Output is semantic-equivalent only. Lossless: false.")

    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Execute the verify command."""
    result = verify_sensor_brk(args.input_path)

    if result["valid"]:
        print("OK: BRK container is valid.")
        print(f"  Profile: {result.get('profile', 'N/A')}")
        print(f"  Model ID: {result.get('model_id', 'N/A')}")
        print("  Note: Validation checks semantic specification integrity,")
        print("  not bit-exact data integrity. Lossless: false.")
        return 0
    else:
        print("FAILED: BRK container verification failed.")
        for err in result.get("errors", []):
            print(f"  - {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
