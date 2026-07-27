"""
uart_builder.py - UART peripheral builder.

Pre-calculates UART baudrate register values.  Currently UART baudrate
is configured via HAL macros (UART_WORDLENGTH_8B etc.), so the builder
primarily validates and normalizes UART configuration for templates.
"""

from __future__ import annotations

import logging
from typing import Any

from ..schemas.hardware import UARTConfig

from .base import PeripheralBuilder
from .registry import register_builder

logger = logging.getLogger("hw2c.uart")


@register_builder("UART_Serial")
class UartBuilder(PeripheralBuilder):
    """Builder for UART/USART serial peripherals."""

    def identify(self, peripheral: dict) -> bool:
        return peripheral.get("type") == "UART_Serial"

    def calculate(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        extra = peripheral.get("extra", {})
        baudrate = int(extra.get("baudrate", 115200))
        instance = peripheral.get("instance", "")
        if not instance:
            instance = _infer_instance(peripheral)
        name = peripheral.get("name", "debug")
        uart_cfg = UARTConfig(
            instance=instance,
            baudrate=baudrate,
            handle_name=f"huart_{name}",
        )
        logger.info(f"UART {name}: {instance} @ {baudrate} baud")
        return {"uart_cfg": uart_cfg}


@register_builder("RS485")
class Rs485Builder(PeripheralBuilder):
    """Builder for RS-485 (DE-controlled UART)."""

    def identify(self, peripheral: dict) -> bool:
        return peripheral.get("type") == "RS485"

    def calculate(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        extra = peripheral.get("extra", {})
        baudrate = int(extra.get("baudrate", 9600))
        uart_ref = peripheral.get("uart", "")
        instance = uart_ref.split("_")[-1] if uart_ref else "UART1"
        name = peripheral.get("name", "rs485")
        uart_cfg = UARTConfig(
            instance=instance,
            baudrate=baudrate,
            handle_name=f"huart_{name}",
        )
        return {"uart_cfg": uart_cfg}


@register_builder("Cellular_4G")
class CellularBuilder(PeripheralBuilder):
    """Builder for Cellular 4G modules (AT-command UART)."""

    def identify(self, peripheral: dict) -> bool:
        return peripheral.get("type") == "Cellular_4G"

    def calculate(self, peripheral: dict, mcu: dict, context: dict) -> dict[str, Any]:
        extra = peripheral.get("extra", {})
        baudrate = int(extra.get("baudrate", 115200))
        uart_ref = peripheral.get("uart", peripheral.get("extra", {}).get("uart", ""))
        instance = uart_ref if uart_ref else "UART2"
        name = peripheral.get("name", "cellular")
        return {"uart_cfg": UARTConfig(
            instance=instance,
            baudrate=baudrate,
            handle_name=f"huart_{name}",
        )}


def _infer_instance(peripheral: dict) -> str:
    """Infer USART/UART instance from peripheral name or uart reference."""
    uart_ref = peripheral.get("uart", "")
    if uart_ref:
        return uart_ref
    name = peripheral.get("name", "")
    if "uart" in name.lower():
        idx = name.lower().replace("uart", "").strip()
        if idx.isdigit():
            return f"USART{idx}"
    return "USART2"  # Default: debug UART
