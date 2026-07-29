"""
STM32 backend implementation.

Wraps the existing context builder pipeline (context/, pin_context, hal_context)
as a TargetBackend. This is the default built-in backend.

MCU-specific data (flash, RAM, core, HAL source prefix) is derived from the
MCU database JSON file loaded at construction time.
"""

import os
from typing import Dict, List, Optional

from ..base import TargetBackend


class STM32Backend(TargetBackend):
    """STM32 backend with HAL + FreeRTOS support.

    Construct with an optional MCU configuration dict to customize
    target-specific parameters. Without it, defaults to STM32G0B1RE.

    Args:
        mcu_config: Optional dict with keys:
            - family       Family prefix (e.g. 'STM32G0')
            - core         Core name (e.g. 'Cortex-M0+')
            - flash_kb     Flash size in KB
            - ram_kb       RAM size in KB
            - max_clock_mhz Max system clock in MHz
            - hal_prefix   HAL library file prefix (e.g. 'stm32g0xx')
    """

    def __init__(self, mcu_config: Optional[Dict] = None):
        self._mcu_config = mcu_config or {}
        family = self._mcu_config.get("family", "STM32G0")
        self._hal_prefix = self._mcu_config.get(
            "hal_prefix",
            f"stm32{family[5:].lower()}xx" if family.startswith("STM32") else "stm32g0xx",
        )

    @classmethod
    def from_mcu_database(cls, mcu_db_path: str) -> "STM32Backend":
        """Create backend from an MCU JSON database file.

        Args:
            mcu_db_path: Path to e.g. STM32G0B1RE.json.

        Returns:
            STM32Backend configured from the JSON data.
        """
        import json
        with open(mcu_db_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        family = raw.get("family", "STM32G0")

        # Extract core info
        cores = raw.get("cores", [])
        core_name = cores[0].get("name", "cm0p") if cores else "cm0p"
        core_map = {"cm0p": "Cortex-M0+", "cm0": "Cortex-M0",
                    "cm3": "Cortex-M3", "cm4": "Cortex-M4",
                    "cm7": "Cortex-M7", "cm33": "Cortex-M33"}
        core = core_map.get(core_name, f"Cortex-{core_name.upper()}")

        # Extract flash/RAM from package data (first package)
        flash_kb = raw.get("flash_kb", 512)
        ram_kb = raw.get("ram_kb", 144)
        max_clock_mhz = raw.get("max_clock_mhz", 64)

        return cls(mcu_config={
            "family": family,
            "core": core,
            "flash_kb": flash_kb,
            "ram_kb": ram_kb,
            "max_clock_mhz": max_clock_mhz,
            "hal_prefix": f"stm32{family[5:].lower()}xx" if family.startswith("STM32") else "stm32g0xx",
        })

    @property
    def mcu_family(self) -> str:
        return self._mcu_config.get("family", "STM32G0")

    def get_mcu_family(self) -> str:
        return self.mcu_family

    def get_template_dirs(self) -> List[str]:
        """Return template directories with priority ordering.

        The main templates/ directory is the only source for STM32.
        Third-party backends can prepend override directories.
        """
        from ...paths import TEMPLATES_DIR
        return [TEMPLATES_DIR]

    def build_pin_context(self, raw_pins: list) -> dict:
        """Delegate to existing pin_context module."""
        from ...context.pin_context import process_pins
        result = {"pins": list(raw_pins)}
        process_pins(raw_pins)
        return result

    def build_clock_context(self, raw_clock: dict) -> dict:
        """Build clock context for STM32.

        Args:
            raw_clock: Clock configuration dict.

        Returns:
            Clock context for templates.
        """
        max_mhz = self._mcu_config.get("max_clock_mhz", 64)
        return {
            "hclk_freq_hz": raw_clock.get("hclk_freq_hz", max_mhz * 1000000),
            "core_clock_mhz": raw_clock.get("core_clock_mhz", max_mhz),
            "hse_freq": raw_clock.get("hse_freq", 8000000),
            "hsi_enabled": raw_clock.get("hsi_enabled", True),
        }

    def get_default_hal_sources(self) -> List[str]:
        """Return core STM32 HAL source files derived from the MCU family prefix.

        The HAL prefix (e.g. 'stm32g0xx') determines which library source
        files are compiled into every project.
        """
        prefix = self._hal_prefix
        return [
            f"{prefix}_hal.c",
            f"{prefix}_hal_cortex.c",
            f"{prefix}_hal_dma.c",
            f"{prefix}_hal_dma_ex.c",
            f"{prefix}_hal_exti.c",
            f"{prefix}_hal_flash.c",
            f"{prefix}_hal_flash_ex.c",
            f"{prefix}_hal_gpio.c",
            f"{prefix}_hal_pwr.c",
            f"{prefix}_hal_pwr_ex.c",
            f"{prefix}_hal_rcc.c",
            f"{prefix}_hal_rcc_ex.c",
            f"{prefix}_hal_rtc.c",
            f"{prefix}_hal_rtc_ex.c",
            f"{prefix}_hal_tim.c",
            f"{prefix}_hal_tim_ex.c",
            f"{prefix}_hal_uart.c",
            f"{prefix}_hal_uart_ex.c",
            f"{prefix}_hal_i2c.c",
            f"{prefix}_hal_i2c_ex.c",
            f"{prefix}_hal_spi.c",
            f"{prefix}_hal_spi_ex.c",
            f"{prefix}_hal_adc.c",
            f"{prefix}_hal_adc_ex.c",
        ]

    def get_mcu_info(self) -> dict:
        """Return MCU metadata from the loaded configuration."""
        return {
            "core": self._mcu_config.get("core", "Cortex-M0+"),
            "flash_kb": self._mcu_config.get("flash_kb", 512),
            "ram_kb": self._mcu_config.get("ram_kb", 144),
            "max_clock_mhz": self._mcu_config.get("max_clock_mhz", 64),
        }

    def validate_pin(self, pin_id: str) -> str or None:
        """Validate STM32G0 pin ID format (e.g., PA2)."""
        import re
        pattern = re.compile(r"^P[A-F][0-9]{1,2}$")
        if not pattern.match(pin_id):
            return f"Invalid STM32 pin ID: {pin_id} (expected e.g. PA2)"
        return None
