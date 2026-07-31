"""
pin.py - Pin configuration IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class PinIR(IRObject):
    """Individual GPIO pin configuration."""

    id: str = ""                # e.g. "PC13"
    function: str = ""          # e.g. "USART2_TX", "GPIO_Output"
    label: str = ""             # e.g. "LED", "BUTTON"
    pull: str = "none"          # "up", "down", "none"
    af: int = 0                 # alternate function number
    notify_task: str = ""       # FreeRTOS task to notify on EXTI
    exti: dict = field(default_factory=dict)
    active_level: str = "high"  # "high" or "low"
