"""
builders/ - Peripheral builder package.

Each peripheral type has a dedicated Builder class that:
  1. Validates the peripheral configuration
  2. Pre-calculates register values (timings, prescalers)
  3. Produces template-ready context dicts

The @register_builder decorator auto-registers builders so that
adding a new peripheral type never requires editing context/builder.py.
"""

from .base import PeripheralBuilder
from .registry import register_builder, get_builder, get_all_builders

__all__ = ["PeripheralBuilder", "register_builder", "get_builder", "get_all_builders"]
