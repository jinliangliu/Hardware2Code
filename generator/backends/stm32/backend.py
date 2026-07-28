"""
STM32 backend implementation.

Wraps the existing context builder pipeline (context/, pin_context, hal_context)
as a TargetBackend. This is the default built-in backend.
"""

import os
from typing import List

from ..base import TargetBackend


class STM32Backend(TargetBackend):
    """STM32G0B1 backend with HAL + FreeRTOS support."""

    MCU_FAMILY = "STM32G0"

    def get_mcu_family(self) -> str:
        return self.MCU_FAMILY

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
        """Build clock context for STM32G0.

        Args:
            raw_clock: Clock configuration dict.

        Returns:
            Clock context for templates.
        """
        return {
            "hclk_freq_hz": raw_clock.get("hclk_freq_hz", 64000000),
            "core_clock_mhz": raw_clock.get("core_clock_mhz", 64),
            "hse_freq": raw_clock.get("hse_freq", 8000000),
            "hsi_enabled": raw_clock.get("hsi_enabled", True),
        }

    def get_default_hal_sources(self) -> List[str]:
        """Return core STM32 HAL source files.

        These are referenced from the static STM32 directory and compiled
        as part of every project. The actual paths are resolved at build time
        via the CMakeLists.txt.
        """
        return [
            "stm32g0xx_hal.c",
            "stm32g0xx_hal_cortex.c",
            "stm32g0xx_hal_dma.c",
            "stm32g0xx_hal_exti.c",
            "stm32g0xx_hal_flash.c",
            "stm32g0xx_hal_flash_ex.c",
            "stm32g0xx_hal_gpio.c",
            "stm32g0xx_hal_pwr.c",
            "stm32g0xx_hal_pwr_ex.c",
            "stm32g0xx_hal_rcc.c",
            "stm32g0xx_hal_rcc_ex.c",
            "stm32g0xx_hal_rtc.c",
            "stm32g0xx_hal_rtc_ex.c",
            "stm32g0xx_hal_tim.c",
            "stm32g0xx_hal_tim_ex.c",
            "stm32g0xx_hal_uart.c",
            "stm32g0xx_hal_uart_ex.c",
            "stm32g0xx_hal_i2c.c",
            "stm32g0xx_hal_i2c_ex.c",
            "stm32g0xx_hal_spi.c",
            "stm32g0xx_hal_spi_ex.c",
            "stm32g0xx_hal_adc.c",
            "stm32g0xx_hal_adc_ex.c",
            "stm32g0xx_hal_dma_ex.c",
        ]

    def get_mcu_info(self) -> dict:
        return {
            "core": "Cortex-M0+",
            "flash_kb": 512,
            "ram_kb": 144,
            "max_clock_mhz": 64,
        }

    def validate_pin(self, pin_id: str) -> str or None:
        """Validate STM32G0 pin ID format (e.g., PA2)."""
        import re
        pattern = re.compile(r"^P[A-F][0-9]{1,2}$")
        if not pattern.match(pin_id):
            return f"Invalid STM32 pin ID: {pin_id} (expected e.g. PA2)"
        return None
