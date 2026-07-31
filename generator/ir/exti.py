"""
exti.py - EXTI interrupt handler IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject
from .pin import PinIR


@dataclass
class ExtiIR(IRObject):
    """EXTI handler grouping — maps IRQ handler names to pin lists."""

    groups: dict[str, list[dict]] = field(default_factory=dict)
