"""Tests for MCUDatabase loader and query methods."""

import json
import os
import tempfile

import pytest

from generator.mcu_database import MCUDatabase


# ---------------------------------------------------------------------------
# Sample JSON fixture
# ---------------------------------------------------------------------------

SAMPLE_JSON = {
    "name": "STM32G0B1RE",
    "family": "STM32G0",
    "peripherals": [
        {
            "name": "USART1",
            "address": 0x40013800,
            "pins": [
                {"pin": "PA9", "signal": "TX", "af": 1},
                {"pin": "PA10", "signal": "RX", "af": 1},
                {"pin": "PB6", "signal": "TX", "af": 0},
                {"pin": "PB7", "signal": "RX", "af": 0},
            ],
        },
        {
            "name": "USART2",
            "address": 0x40004400,
            "pins": [
                {"pin": "PA2", "signal": "TX", "af": 1},
                {"pin": "PA3", "signal": "RX", "af": 1},
                {"pin": "PA14", "signal": "TX", "af": 1},
                {"pin": "PA15", "signal": "RX", "af": 1},
            ],
        },
        {
            "name": "I2C1",
            "address": 0x40005400,
            "pins": [
                {"pin": "PB6", "signal": "SCL", "af": 1},
                {"pin": "PB7", "signal": "SDA", "af": 1},
                {"pin": "PB8", "signal": "SCL", "af": 1},
                {"pin": "PB9", "signal": "SDA", "af": 1},
            ],
        },
        {
            "name": "ADC1",
            "address": 0x40012400,
            "pins": [
                {"pin": "PA0", "signal": "IN0"},
                {"pin": "PA1", "signal": "IN1"},
                {"pin": "PA2", "signal": "IN2"},
                {"pin": "PA3", "signal": "IN3"},
            ],
        },
        {
            "name": "TIM2",
            "address": 0x40000000,
            "pins": [
                {"pin": "PA0", "signal": "CH1", "af": 1},
                {"pin": "PA1", "signal": "CH2", "af": 1},
                {"pin": "PA5", "signal": "CH1", "af": 2},
            ],
        },
    ],
}


@pytest.fixture
def sample_db():
    """Create MCUDatabase from sample JSON data."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE_JSON, f)
        tmp_path = f.name
    db = MCUDatabase.from_json(tmp_path)
    os.unlink(tmp_path)
    return db


# ---------------------------------------------------------------------------
# Tests: from_json
# ---------------------------------------------------------------------------


def test_from_json_loads_correctly(sample_db):
    assert sample_db.name == "STM32G0B1RE"
    assert sample_db.family == "STM32G0"


def test_from_json_file_not_found():
    with pytest.raises(FileNotFoundError):
        MCUDatabase.from_json("/nonexistent/path.json")


# ---------------------------------------------------------------------------
# Tests: from_mcu_name
# ---------------------------------------------------------------------------


def test_from_mcu_name_auto_discovery():
    """Test that from_mcu_name finds the actual JSON file in data/mcu/."""
    db = MCUDatabase.from_mcu_name("STM32G0B1RET6")
    assert "STM32G0" in db.family
    assert db.is_valid_pin("PA0")
    assert db.is_valid_pin("PC13")


# ---------------------------------------------------------------------------
# Tests: get_pin
# ---------------------------------------------------------------------------


def test_get_pin_valid(sample_db):
    info = sample_db.get_pin("PA2")
    assert info is not None
    assert info["pin"] == "PA2"
    signals = info["signals"]
    assert len(signals) >= 2  # USART2_TX + ADC1_IN2


def test_get_pin_invalid(sample_db):
    assert sample_db.get_pin("PX99") is None


def test_get_pin_case_insensitive(sample_db):
    assert sample_db.get_pin("pa2") is not None
    assert sample_db.get_pin("Pa2") is not None


# ---------------------------------------------------------------------------
# Tests: get_pin_af_functions
# ---------------------------------------------------------------------------


def test_get_pin_af_functions(sample_db):
    funcs = sample_db.get_pin_af_functions("PA2")
    # Should contain USART2_TX (af=1) but NOT ADC1_IN2 (af=None)
    assert "USART2_TX" in funcs
    assert "ADC1_IN2" not in funcs


# ---------------------------------------------------------------------------
# Tests: get_peripheral_pins
# ---------------------------------------------------------------------------


def test_get_peripheral_pins(sample_db):
    pins = sample_db.get_peripheral_pins("USART1")
    assert set(pins) == {"PA9", "PA10", "PB6", "PB7"}


def test_get_peripheral_pins_unknown(sample_db):
    assert sample_db.get_peripheral_pins("SPI99") == []


# ---------------------------------------------------------------------------
# Tests: get_peripheral_signals
# ---------------------------------------------------------------------------


def test_get_peripheral_signals(sample_db):
    signals = sample_db.get_peripheral_signals("I2C1")
    assert len(signals) >= 4
    assert {"pin": "PB6", "signal": "SCL", "af": 1} in signals


# ---------------------------------------------------------------------------
# Tests: is_valid_pin
# ---------------------------------------------------------------------------


def test_is_valid_pin(sample_db):
    assert sample_db.is_valid_pin("PA0") is True
    assert sample_db.is_valid_pin("PA10") is True
    assert sample_db.is_valid_pin("PZ99") is False


# ---------------------------------------------------------------------------
# Tests: resolve_pin_function
# ---------------------------------------------------------------------------


def test_resolve_pin_function(sample_db):
    assert sample_db.resolve_pin_function("PA2", "USART2", "TX") == 1
    assert sample_db.resolve_pin_function("PA3", "USART2", "RX") == 1
    assert sample_db.resolve_pin_function("PB6", "I2C1", "SCL") == 1
    # ADC pins have no AF (analog mode)
    assert sample_db.resolve_pin_function("PA0", "ADC1", "IN0") is None


def test_resolve_pin_function_not_supported(sample_db):
    assert sample_db.resolve_pin_function("PA0", "USART1", "TX") is None


# ---------------------------------------------------------------------------
# Tests: peripheral info
# ---------------------------------------------------------------------------


def test_get_peripheral_info(sample_db):
    info = sample_db.get_peripheral_info("USART1")
    assert info is not None
    assert info["address"] == 0x40013800


def test_get_peripheral_info_missing(sample_db):
    assert sample_db.get_peripheral_info("NONEXISTENT") is None


# ---------------------------------------------------------------------------
# Tests: list_peripherals
# ---------------------------------------------------------------------------


def test_list_peripherals(sample_db):
    periphs = sample_db.list_peripherals()
    assert "USART1" in periphs
    assert "USART2" in periphs
    assert "I2C1" in periphs
    assert "ADC1" in periphs
    assert "TIM2" in periphs


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


def test_empty_json():
    empty = {"name": "Empty", "family": "Test"}
    db = MCUDatabase("Empty", "Test", empty)
    assert db.list_peripherals() == []
    assert db.get_pin("PA0") is None


def test_deduplication():
    """Duplicate (peripheral, signal, pin) entries should be deduplicated."""
    dup = {
        "name": "Test",
        "family": "Test",
        "peripherals": [
            {
                "name": "GPIOA",
                "pins": [
                    {"pin": "PA0", "signal": "OUT", "af": 0},
                    {"pin": "PA0", "signal": "OUT", "af": 0},  # duplicate
                ],
            }
        ],
    }
    db = MCUDatabase("Test", "Test", dup)
    signals = db.get_pin_signals("PA0")
    assert len(signals) == 1
