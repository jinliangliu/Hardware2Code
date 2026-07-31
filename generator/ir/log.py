"""
log.py - Log subsystem configuration IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class LogIR(IRObject):
    """Logging subsystem configuration."""

    enabled: bool = False
    ring_buf_size: int = 1024
    # UART hardware mapping
    uart_instance: str = ""
    uart_irqn: str = ""
    uart_rcc_clk: str = ""
    uart_ccipr_sel_msk: str = ""
    uart_ccipr_hsi_src: str = ""
    # TX pin
    tx_port: str = ""
    tx_pin: str = ""
    tx_af: str = ""
    # RX pin
    rx_port: str = ""
    rx_pin: str = ""
    rx_af: str = ""
    # GPIO clock enable
    rcc_gpio_clk: str = ""
