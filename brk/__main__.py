"""
Allow running BRK as: python -m brk
"""

from brk.cli import main
import sys

sys.exit(main())
