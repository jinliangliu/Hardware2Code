"""Tests for generator/context/bootloader_context.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context.bootloader_context import (build_boot_config,
                                          inject_bootloader_drivers,
                                          get_boot_led_pin)


def test_build_boot_config_disabled():
    """Bootloader disabled returns empty config and False"""
    config, enabled = build_boot_config({})
    assert enabled == False
    assert config == {}


def test_build_boot_config_enabled_minimal():
    """Bootloader enabled with minimal config"""
    config, enabled = build_boot_config({"enabled": True})
    assert enabled == True
    assert config["size_kb"] == 8
    assert config["app_a_offset"] == 0x2000
    assert config["app_b_offset"] == 0x40000
    assert config["wdg_timeout_ms"] == 5000
    assert config["max_retries"] == 3


def test_build_boot_config_custom_values():
    """Bootloader with custom values preserves them"""
    config, enabled = build_boot_config({
        "enabled": True,
        "size_kb": 16,
        "app_a_offset": 0x4000,
        "wdg_timeout_ms": 8000,
        "max_retries": 5
    })
    assert config["size_kb"] == 16
    assert config["app_a_offset"] == 0x4000
    assert config["wdg_timeout_ms"] == 8000
    assert config["max_retries"] == 5


def test_build_boot_config_calculates_iwdg_reload():
    """Bootloader computes iwdg_reload_value"""
    config, enabled = build_boot_config({"enabled": True, "wdg_timeout_ms": 5000})
    # 5000ms / 8ms per tick = 625, within 12-bit range
    assert config["iwdg_reload_value"] == 625


def test_inject_bootloader_drivers_no_bootloader():
    """No bootloader means no injections"""
    result = inject_bootloader_drivers(False, False, {}, "")
    assert result["has_fota"] == False
    assert len(result["drivers_additions"]) == 0
    assert len(result["hal_additions"]) == 0


def test_inject_bootloader_drivers_with_bootloader_no_uart():
    """Bootloader without UART: IWDG only, no FOTA"""
    result = inject_bootloader_drivers(True, False, {"wdg_timeout_ms": 5000}, "")
    assert result["has_fota"] == False
    assert len(result["drivers_additions"]) == 1  # IWDG only
    assert result["drivers_additions"][0]["name"] == "iwdg"


def test_inject_bootloader_drivers_with_fota():
    """Bootloader + UART: IWDG + FOTA + bspatch"""
    result = inject_bootloader_drivers(True, True, {"wdg_timeout_ms": 5000}, "uart1")
    assert result["has_fota"] == True
    assert len(result["drivers_additions"]) == 3  # IWDG + FOTA + bspatch
    names = [d["name"] for d in result["drivers_additions"]]
    assert "iwdg" in names
    assert "fota" in names
    assert "fota_bspatch" in names


def test_get_boot_led_pin_found():
    """LED pin extracted from pins list when label == 'LED'"""
    pins = [{"id": "PA5", "function": "GPIO_Output", "label": "LED"}]
    result = get_boot_led_pin(pins)
    assert result["boot_led_port"] == "GPIOA"
    assert result["boot_led_pin_num"] == 5
    assert result["boot_led_rcc_enable"] == "RCC_IOPENR_GPIOAEN"


def test_get_boot_led_pin_fallback():
    """No LED pin in list → fallback to GPIOC / pin 0"""
    pins = [{"id": "PB3", "function": "GPIO_Input", "label": "BUTTON"}]
    result = get_boot_led_pin(pins)
    assert result["boot_led_port"] == "GPIOC"
    assert result["boot_led_pin_num"] == 0
    assert result["boot_led_rcc_enable"] == "RCC_IOPENR_GPIOCEN"


def test_get_boot_led_pin_empty():
    """Empty pins list → fallback"""
    result = get_boot_led_pin([])
    assert result["boot_led_port"] == "GPIOC"
    assert result["boot_led_pin_num"] == 0


def test_build_boot_config_computes_slot_addresses():
    """Default config computes correct slot addresses for 512KB flash"""
    config, enabled = build_boot_config({"enabled": True})
    assert config["_app_a_start"] == 0x08002000
    assert config["_app_a_end"]   == 0x08040000
    assert config["_app_b_start"] == 0x08040000
    assert config["_app_b_end"]   == 0x08080000
    assert config["_app_a_size"]  == 0x3E000   # 248KB
    assert config["_app_b_size"]  == 0x40000   # 256KB


def test_build_boot_config_slot_addresses_custom():
    """Custom offsets produce correct computed addresses"""
    config, enabled = build_boot_config({
        "enabled": True,
        "size_kb": 16,
        "app_a_offset": 0x4000,
        "app_b_offset": 0x30000,
    })
    assert config["_app_a_start"] == 0x08004000
    assert config["_app_a_end"]   == 0x08030000
    assert config["_app_b_start"] == 0x08030000
    assert config["_app_b_end"]   == 0x08080000
    assert config["_app_a_size"]  == 0x2C000
    assert config["_app_b_size"]  == 0x50000


if __name__ == "__main__":
    test_build_boot_config_disabled()
    test_build_boot_config_enabled_minimal()
    test_build_boot_config_custom_values()
    test_build_boot_config_calculates_iwdg_reload()
    test_inject_bootloader_drivers_no_bootloader()
    test_inject_bootloader_drivers_with_bootloader_no_uart()
    test_inject_bootloader_drivers_with_fota()
    test_get_boot_led_pin_found()
    test_get_boot_led_pin_fallback()
    test_get_boot_led_pin_empty()
    test_build_boot_config_computes_slot_addresses()
    test_build_boot_config_slot_addresses_custom()
    print("All bootloader_context tests passed.")
