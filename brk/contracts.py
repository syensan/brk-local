"""
BRK Contract definitions and validation.

A BRK contract specifies what reconstruction tasks the container supports,
what tolerances are acceptable, and what hard constraints must be preserved.

IMPORTANT: BRK contracts always have lossless=false, bit_exact_reconstruction=false,
semantic_equivalent=true.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brk.constants import (
    FLAG_BIT_EXACT_RECONSTRUCTION,
    FLAG_LOSSLESS,
    FLAG_SEMANTIC_EQUIVALENT,
)
from brk.errors import InvalidContract


@dataclass
class BRKContract:
    """Represents a BRK reconstruction contract.

    BRK is NOT a universal lossless compressor.
    This contract defines the semantic equivalence guarantees.
    """

    mode: str = "brk-task"
    domain: str = "agricultural_sensor"
    lossless: bool = field(default=False, init=False)
    bit_exact_reconstruction: bool = field(default=False, init=False)
    semantic_equivalent: bool = field(default=True, init=False)
    tasks: list[str] = field(
        default_factory=lambda: [
            "daily_statistics",
            "trend_reconstruction",
            "anomaly_preservation",
        ]
    )
    tolerances: dict[str, float] = field(
        default_factory=lambda: {
            "temperature_rmse_celsius": 0.5,
            "humidity_rmse_percent": 3.0,
            "soil_moisture_rmse_percent": 2.0,
            "anomaly_time_error_minutes": 10.0,
        }
    )
    hard_constraints: list[str] = field(
        default_factory=lambda: [
            "preserve_sensor_count",
            "preserve_detected_anomalies",
        ]
    )

    def __post_init__(self) -> None:
        """Enforce safety invariants after initialization."""
        validate_contract(self)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this contract to a dictionary."""
        return {
            "mode": self.mode,
            "domain": self.domain,
            "lossless": self.lossless,
            "bit_exact_reconstruction": self.bit_exact_reconstruction,
            "semantic_equivalent": self.semantic_equivalent,
            "tasks": self.tasks,
            "tolerances": self.tolerances,
            "hard_constraints": self.hard_constraints,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BRKContract:
        """Create a BRKContract from a dictionary.

        The lossless/bit_exact_reconstruction/semantic_equivalent fields
        from the dict are IGNORED — the class enforces its own values.
        """
        contract = cls(
            mode=d.get("mode", "brk-task"),
            domain=d.get("domain", "agricultural_sensor"),
        )
        # Override collections from dict, but safety flags remain enforced
        if "tasks" in d:
            contract.tasks = list(d["tasks"])
        if "tolerances" in d:
            contract.tolerances = dict(d["tolerances"])
        if "hard_constraints" in d:
            contract.hard_constraints = list(d["hard_constraints"])
        return contract


def validate_contract(contract: BRKContract) -> None:
    """Validate that a BRK contract satisfies safety invariants.

    BRK is NOT a universal lossless compressor.
    These invariants MUST hold:
      - lossless == False
      - bit_exact_reconstruction == False
      - semantic_equivalent == True
    """
    if contract.lossless is not False:
        raise InvalidContract(
            f"contract.lossless must be False, got {contract.lossless!r}. "
            "BRK is not a universal lossless compressor."
        )
    if contract.bit_exact_reconstruction is not False:
        raise InvalidContract(
            f"contract.bit_exact_reconstruction must be False, got {contract.bit_exact_reconstruction!r}. "
            "BRK does not guarantee bit-exact reconstruction."
        )
    if contract.semantic_equivalent is not True:
        raise InvalidContract(
            f"contract.semantic_equivalent must be True, got {contract.semantic_equivalent!r}. "
            "BRK guarantees semantic equivalence, not bit-exact reconstruction."
        )


def validate_contract_dict(d: dict[str, Any]) -> None:
    """Validate a contract dictionary for safety invariants.

    Used when validating .brk files that are read from disk.
    """
    if d.get("lossless") is not False:
        raise InvalidContract(
            f"contract.lossless must be False, got {d.get('lossless')!r}. "
            "BRK is not a universal lossless compressor."
        )
    if d.get("bit_exact_reconstruction") is not False:
        raise InvalidContract(
            f"contract.bit_exact_reconstruction must be False, got {d.get('bit_exact_reconstruction')!r}. "
            "BRK does not guarantee bit-exact reconstruction."
        )
    if d.get("semantic_equivalent") is not True:
        raise InvalidContract(
            f"contract.semantic_equivalent must be True, got {d.get('semantic_equivalent')!r}. "
            "BRK guarantees semantic equivalence, not bit-exact reconstruction."
        )


def validate_flags_dict(flags: dict[str, Any]) -> None:
    """Validate header flags for safety invariants."""
    if flags.get("lossless") is not FLAG_LOSSLESS:
        raise InvalidContract(
            f"header.flags.lossless must be {FLAG_LOSSLESS!r}, got {flags.get('lossless')!r}. "
            "BRK is not a universal lossless compressor."
        )
    if flags.get("bit_exact_reconstruction") is not FLAG_BIT_EXACT_RECONSTRUCTION:
        raise InvalidContract(
            f"header.flags.bit_exact_reconstruction must be {FLAG_BIT_EXACT_RECONSTRUCTION!r}, "
            f"got {flags.get('bit_exact_reconstruction')!r}. "
            "BRK does not guarantee bit-exact reconstruction."
        )
    if flags.get("semantic_equivalent") is not FLAG_SEMANTIC_EQUIVALENT:
        raise InvalidContract(
            f"header.flags.semantic_equivalent must be {FLAG_SEMANTIC_EQUIVALENT!r}, "
            f"got {flags.get('semantic_equivalent')!r}. "
            "BRK guarantees semantic equivalence, not bit-exact reconstruction."
        )


def default_contract() -> BRKContract:
    """Return a default BRK-Sensor contract."""
    return BRKContract()
