"""
base.py - Abstract base class for peripheral builders.

Every peripheral type (GPIO, I2C, SPI, UART, etc.) implements a subclass
of PeripheralBuilder.  The base class defines the contract:
  - identify()   — return True if this builder handles the peripheral
  - calculate()  — pre-compute register values, timing, prescalers
  - build()      — produce a context dict for template rendering

Adding a new peripheral type only requires:
  1. A new builder module (e.g. builders/can_builder.py)
  2. A class decorated with @register_builder("CAN")
  3. A Jinja2 template (e.g. templates/drivers/drv_can.c.j2)

No other file needs modification.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger("hw2c.builder")


class PeripheralBuilder(ABC):
    """Abstract base for a peripheral context builder.

    Subclasses _must_ override `calculate()` and optionally `identify()`.
    """

    # Peripheral type string this builder handles (set by @register_builder)
    peripheral_type: str = ""

    def identify(self, peripheral: dict) -> bool:
        """Check whether this builder should handle the given peripheral.

        Default: match by peripheral_type string.  Override for sub-types
        (e.g. a "i2c_sensor" builder that handles I2C_Sensor_MPU6050 and
        I2C_EEPROM with different calculate() logic).
        """
        return peripheral.get("type") == self.peripheral_type

    @abstractmethod
    def calculate(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        """Pre-compute register values and derived parameters.

        Called once per peripheral before template rendering.
        Must NOT modify the template context — returns a dict that is
        merged into the peripheral entry.

        Args:
            peripheral: The raw peripheral dict from YAML (validated).
            mcu: MCU configuration dict (clock speeds, etc.).
            context: Partial build context accumulated so far.

        Returns:
            Dict of computed values (e.g. {"i2c": I2CConfig(...)})
            that will be merged into the peripheral entry.
        """
        ...

    def build(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        """Build the full context contribution for this peripheral.

        Default implementation: calls calculate() and merges result.
        Override to add pins, HAL sources, or other side effects.
        """
        computed = self.calculate(peripheral, mcu, context)
        return {
            "computed": computed,
            "flags": set(),
            "hal_sources": [],
            "pins": [],
        }
