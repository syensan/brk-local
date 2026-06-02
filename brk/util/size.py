"""
Size formatting and budget utilities for BRK.
"""

from __future__ import annotations


def format_size(n_bytes: int) -> str:
    """Format a byte count as a human-readable string.

    Examples:
      512 -> "512 B"
      1024 -> "1.00 KB"
      1048576 -> "1.00 MB"
    """
    if n_bytes < 1024:
        return f"{n_bytes} B"
    elif n_bytes < 1024 * 1024:
        return f"{n_bytes / 1024:.2f} KB"
    else:
        return f"{n_bytes / (1024 * 1024):.2f} MB"


def within_budget(actual_bytes: int, budget_bytes: int) -> bool:
    """Check whether the actual size is within the target budget."""
    return actual_bytes <= budget_bytes
