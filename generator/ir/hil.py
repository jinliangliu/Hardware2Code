"""
hil.py - HIL (Hardware-In-the-Loop) configuration IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class HilIR(IRObject):
    """HIL test infrastructure configuration."""

    baudrate: int = 115200
    uart: str = "UART2"
    tx_pin: str = "PA2"
    rx_pin: str = "PA3"
    tests: list[dict] = field(default_factory=list)
