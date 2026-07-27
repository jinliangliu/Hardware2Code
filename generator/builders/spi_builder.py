"""
spi_builder.py - SPI peripheral builder.

Pre-calculates SPI baudrate prescaler based on peripheral clock and
requested speed, replacing hardcoded SPI_BAUDRATEPRESCALER_8 in templates.
"""

from __future__ import annotations

import logging
from typing import Any

from ..schemas.hardware import SPIConfig

from .base import PeripheralBuilder
from .registry import register_builder

logger = logging.getLogger("hw2c.spi")

# SPI peripheral clock on STM32G0B1 = PCLK1 = HCLK = 16 MHz (HSI default)
_SPI_CLK_HZ_DEFAULT = 16_000_000

# SPI baudrate prescaler enum values -> divisor mapping
_PRESCALER_MAP: dict[int, int] = {
    2: 0x00,    # SPI_BAUDRATEPRESCALER_2
    4: 0x08,    # SPI_BAUDRATEPRESCALER_4
    8: 0x10,    # SPI_BAUDRATEPRESCALER_8
    16: 0x18,   # SPI_BAUDRATEPRESCALER_16
    32: 0x20,   # SPI_BAUDRATEPRESCALER_32
    64: 0x28,   # SPI_BAUDRATEPRESCALER_64
    128: 0x30,  # SPI_BAUDRATEPRESCALER_128
    256: 0x38,  # SPI_BAUDRATEPRESCALER_256
}


@register_builder("SPI_Flash_W25Q32")
class SpiFlashBuilder(PeripheralBuilder):
    """Builder for SPI flash peripherals (W25Q32, generic SPI flash)."""

    def identify(self, peripheral: dict) -> bool:
        ptype = peripheral.get("type", "")
        return ptype in ("SPI_Flash_W25Q32", "SPI_Flash_Generic")

    def calculate(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        bus = peripheral.get("bus", "SPI1")
        bus_index = int(bus[-1]) if bus[-1].isdigit() else 1
        target_speed = peripheral.get("extra", {}).get("spi_speed_hz", 1_000_000)
        prescaler = _calc_spi_prescaler(_SPI_CLK_HZ_DEFAULT, target_speed)
        prescaler_code = _PRESCALER_MAP.get(prescaler, 0x10)
        spi_cfg = SPIConfig(
            instance=bus,
            bus_index=bus_index,
            prescaler=prescaler,
            handle_name=f"hspi{bus_index}",
        )
        logger.info(
            f"SPI {bus}: prescaler={prescaler} (code=0x{prescaler_code:02X}) "
            f"for {target_speed}Hz @ {_SPI_CLK_HZ_DEFAULT}Hz"
        )
        return {
            "spi": spi_cfg,
            "spi_prescaler_code": prescaler_code,
        }


@register_builder("SPI_Flash_Generic")
class SpiFlashGenericBuilder(SpiFlashBuilder):
    """Generic SPI flash — same SPI calculation."""

    def identify(self, peripheral: dict) -> bool:
        return peripheral.get("type") == "SPI_Flash_Generic"


def _calc_spi_prescaler(spi_clk_hz: int, target_speed_hz: int) -> int:
    """Find the smallest prescaler divisor that keeps SCK <= target_speed.

    Returns: prescaler divisor (2, 4, 8, 16, 32, 64, 128, 256).
    """
    divisors = sorted(_PRESCALER_MAP.keys())
    for div in divisors:
        actual_speed = spi_clk_hz // div
        if actual_speed <= target_speed_hz:
            return div
    return 256  # Slowest fallback
