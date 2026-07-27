"""
i2c_builder.py - I2C peripheral builder.

Pre-calculates I2C TIMINGR register value based on peripheral clock and
requested speed, replacing the hardcoded 0x2000090E in templates.
"""

from __future__ import annotations

import logging
from typing import Any

from ..schemas.hardware import I2CConfig

from .base import PeripheralBuilder
from .registry import register_builder

logger = logging.getLogger("hw2c.i2c")

# I2C peripheral clock on STM32G0B1 = PCLK1 = HCLK = 16 MHz (HSI default)
_I2C_CLK_HZ_DEFAULT = 16_000_000


@register_builder("I2C_Sensor_MPU6050")
class I2cMpu6050Builder(PeripheralBuilder):
    """Builder for I2C sensor peripherals (MPU6050, EEPROM)."""

    def identify(self, peripheral: dict) -> bool:
        ptype = peripheral.get("type", "")
        return ptype in ("I2C_Sensor_MPU6050", "I2C_EEPROM")

    def calculate(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        bus = peripheral.get("bus", "I2C1")
        bus_index = int(bus[-1]) if bus[-1].isdigit() else 1
        speed_hz = peripheral.get("extra", {}).get("speed_hz", 100_000)
        timing = _calc_i2c_timing(_I2C_CLK_HZ_DEFAULT, speed_hz)
        i2c_cfg = I2CConfig(
            instance=bus,
            bus_index=bus_index,
            timing_r=timing,
            speed_hz=speed_hz,
        )
        logger.info(f"I2C {bus}: TIMINGR=0x{timing:08X} for {speed_hz}Hz @ {_I2C_CLK_HZ_DEFAULT}Hz")
        return {"i2c": i2c_cfg}


@register_builder("I2C_EEPROM")
class I2cEepromBuilder(I2cMpu6050Builder):
    """Builder for I2C EEPROM peripherals — same I2C timing calculation."""

    def identify(self, peripheral: dict) -> bool:
        return peripheral.get("type") == "I2C_EEPROM"


def _calc_i2c_timing(i2c_clk_hz: int, target_speed_hz: int) -> int:
    """Calculate I2C TIMINGR register value for STM32G0.

    Uses the standard formula from STM32 reference manual:
      t_SCL = t_SYSCLK * (PRESC+1) * (SCLL+1 + SCLH+1 + 2)
    where t_SYSCLK = 1 / i2c_clk_hz.

    For simplicity, this uses a lookup table approach common in STM32Cube.
    For STM32G0B1 @ 16 MHz I2C clock:

      100 kHz standard mode:
        PRESC = 0, SCLL = 0x13 (19), SCLH = 0x0F (15)
        TIMINGR = 0x0000 0F13

    Returns TIMINGR register value (32-bit).
    """
    # Lookup table: (i2c_clk_mhz, target_khz) -> TIMINGR value
    # Pre-computed with STM32CubeMX methodology
    timing_map = {
        # 16 MHz I2C clock
        (16, 100): 0x00000F13,   # Standard mode 100 kHz
        (16, 400): 0x00000307,   # Fast mode 400 kHz
        # 64 MHz I2C clock (if PLL enabled)
        (64, 100): 0x00303D5B,
        (64, 400): 0x00100D13,
    }

    i2c_mhz = i2c_clk_hz // 1_000_000
    target_khz = target_speed_hz // 1000

    key = (i2c_mhz, target_khz)
    if key in timing_map:
        return timing_map[key]

    # Fallback: use the default 100 kHz @ 16 MHz value
    logger.warning(
        f"No I2C timing table entry for {i2c_mhz}MHz @ {target_khz}kHz, "
        f"using default 100kHz @ 16MHz"
    )
    return 0x00000F13
