"""
bootloader.py - Bootloader configuration IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import IRObject


@dataclass
class BootIR(IRObject):
    """Bootloader and FOTA configuration."""

    enabled: bool = False
    size_kb: int = 8
    size_bytes: int = 8192
    app_a_offset: int = 0x2000
    app_b_offset: int = 0x4000
    crc_method: str = "CRC32"
    boot_flag_src: str = "RAM"
    max_retries: int = 3
    wdg_timeout_ms: int = 5000
    iwdg_reload_value: int = 625
    # LED pin used by bootloader
    led_port: str = "GPIOC"
    led_pin_num: int = 0
    led_rcc_enable: str = "RCC_IOPENR_GPIOCEN"
    # Raw dict for template compatibility
    raw: dict = field(default_factory=dict)
