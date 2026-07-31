"""
mcu.py - MCU configuration IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class McuIR(IRObject):
    """MCU configuration: part number, clock tree, and derived fields."""

    part: str = ""
    core: str = "Cortex-M0+"
    core_clock_mhz: int = 16
    clock_source: str = "HSI"
    clock_freq_hz: int = 16000000
    hse_freq: int = 8000000
    hclk_freq_hz: int = 16000000  # same as clock_freq_hz
    flash_kb: int = 512
