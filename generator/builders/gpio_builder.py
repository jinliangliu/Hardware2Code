"""
gpio_builder.py - GPIO peripheral builder.

Pre-calculates MX_GPIO_Init parameters for all pins, grouping them
by port to avoid redundant HAL_GPIO_Init calls.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import PeripheralBuilder
from .registry import register_builder

logger = logging.getLogger("hw2c.gpio")

# Pin function -> GPIO InitTypeDef parameter mapping.
# For output pins (GPIO_Output, SPI_NSS): Mode = OUTPUT_PP, Speed = LOW
# For input pins: Mode = INPUT, Pull = NOPULL (or up/down per config)
# For alternate function pins (I2C, SPI, UART): Mode = AF_PP, Speed = LOW

_OUTPUT_FUNCTIONS = frozenset({
    "GPIO_Output",
})

_INPUT_FUNCTIONS = frozenset({
    "GPIO_Input",
})

_AF_FUNCTIONS = frozenset({
    "I2C_SCL", "I2C_SDA",
    "SPI_SCK", "SPI_MISO", "SPI_MOSI", "SPI_NSS",
    "UART_TX", "UART_RX", "USART_TX", "USART_RX",
    "LPUART_TX", "LPUART_RX",
    "RS485_DE",
})


@register_builder("GPIO")
class GpioBuilder(PeripheralBuilder):
    """Builder that processes all GPIO pins into MX_GPIO_Init structures."""

    peripheral_type = "GPIO"

    def identify(self, peripheral: dict) -> bool:
        # GPIO builder handles ALL pins, not a specific peripheral
        return False  # Not auto-triggered by peripherals — called from context builder

    def calculate(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        return {}

    def build(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        return {"computed": {}, "flags": set(), "hal_sources": [], "pins": []}

    @staticmethod
    def build_pin_groups(pins: list[dict]) -> list[dict]:
        """Group pins by port and produce MX_GPIO_Init parameter blocks.

        Each group:
          - port: GPIO port letter (A, B, C, ...)
          - pins: list of dicts {pin, mode, pull, speed, alt}
          - init_calls: list of 'HAL_GPIO_Init(GPIOx, &gpio_init)' stmts

        Returns list of port groups usable in gpio.c.j2 template.
        """
        groups: dict[str, list[dict]] = {}
        for pin in pins:
            port = pin["id"][1]
            groups.setdefault(port, []).append(pin)

        result: list[dict] = []
        for port, port_pins in sorted(groups.items()):
            pin_entries: list[dict] = []
            for p in port_pins:
                func = p.get("function", "GPIO_Output")
                entry = _compute_pin_entry(p, func)
                pin_entries.append(entry)
            result.append({
                "port": port,
                "port_name": f"GPIO{port}",
                "pins": pin_entries,
            })

        return result


def _compute_pin_entry(pin: dict, func: str) -> dict:
    """Compute the GPIO_InitTypeDef parameters for a single pin.

    Returns dict with keys: pin_name, mode, pull, speed, alternate, comment.
    """
    pin_name = f"GPIO_PIN_{pin['id'][2:]}"
    pin_num = int(pin["id"][2:])
    pull = pin.get("pull", "")

    # Determine pull mode
    if pull == "up":
        pull_mode = "GPIO_PULLUP"
    elif pull == "down":
        pull_mode = "GPIO_PULLDOWN"
    else:
        pull_mode = "GPIO_NOPULL"

    # Determine mode based on function
    if func in _OUTPUT_FUNCTIONS:
        mode = "GPIO_MODE_OUTPUT_PP"
        speed = "GPIO_SPEED_FREQ_LOW"
        alt = 0
    elif func in _INPUT_FUNCTIONS:
        mode = "GPIO_MODE_INPUT"
        speed = "GPIO_SPEED_FREQ_LOW"
        alt = 0
    elif func.startswith("ADC_IN"):
        mode = "GPIO_MODE_ANALOG"
        speed = "GPIO_SPEED_FREQ_LOW"
        alt = 0
    elif func in ("IR_OUT",):
        mode = "GPIO_MODE_OUTPUT_PP"
        speed = "GPIO_SPEED_FREQ_LOW"
        alt = 0
    elif func in ("CELL_PWR", "CELL_RST"):
        mode = "GPIO_MODE_OUTPUT_PP"
        speed = "GPIO_SPEED_FREQ_LOW"
        alt = 0
    elif func in _AF_FUNCTIONS or any(func.startswith(prefix) for prefix in
                                       ("I2C", "SPI", "UART", "USART", "LPUART", "RS485")):
        mode = "GPIO_MODE_AF_PP"
        speed = "GPIO_SPEED_FREQ_LOW"
        alt = pin.get("af", 0)
    else:
        mode = "GPIO_MODE_OUTPUT_PP"
        speed = "GPIO_SPEED_FREQ_LOW"
        alt = 0

    return {
        "pin_name": pin_name,
        "pin_num": pin_num,
        "mode": mode,
        "pull": pull_mode,
        "speed": speed,
        "alt": alt,
        "comment": f"/* {pin['id']}: {func} */",
    }
