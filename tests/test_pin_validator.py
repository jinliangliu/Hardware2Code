"""Tests for pin conflict validator."""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

from generator.mcu_database import MCUDatabase
from generator.validators.pin_conflict_validator import (
    PinConflictError,
    InvalidPinError,
    PeripheralPinRefError,
    UnsupportedFunctionError,
    validate_pin_conflicts,
    _parse_function,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mock_hw(pins):
    """Create a mock HardwareModel with the given pins."""
    hw = MagicMock()
    hw.pins = []
    for p in pins:
        pin = MagicMock()
        pin.id = p[0]
        pin.function = p[1]
        pin.label = p[2] if len(p) > 2 else None
        hw.pins.append(pin)
    hw.peripherals = []
    return hw


def _make_mock_peri(name, ptype, **fields):
    """Create a mock peripheral with top-level fields + extra dict."""
    peri = MagicMock()
    peri.name = name
    peri.type = ptype
    peri.extra = dict(fields.pop("extra", {}))
    peri.uart = None
    for f in ("cs_pin", "chip_select_pin", "tx_pin", "rx_pin",
              "de_pin", "rs485_de_pin"):
        setattr(peri, f, None)
    for k, v in fields.items():
        setattr(peri, k, v)
    return peri


SAMPLE_JSON = {
    "name": "STM32G0B1RE",
    "family": "STM32G0",
    "peripherals": [
        {
            "name": "USART2",
            "pins": [
                {"pin": "PA2", "signal": "TX", "af": 1},
                {"pin": "PA3", "signal": "RX", "af": 1},
            ],
        },
        {
            "name": "I2C1",
            "pins": [
                {"pin": "PB6", "signal": "SCL", "af": 1},
                {"pin": "PB7", "signal": "SDA", "af": 1},
            ],
        },
        {
            "name": "TIM2",
            "pins": [
                {"pin": "PA0", "signal": "CH1", "af": 1},
                {"pin": "PA2", "signal": "CH2", "af": 2},
            ],
        },
        {
            "name": "ADC1",
            "pins": [
                {"pin": "PA0", "signal": "IN0"},
                {"pin": "PA1", "signal": "IN1"},
            ],
        },
    ],
}


@pytest.fixture
def sample_db():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(SAMPLE_JSON, f)
        tmp_path = f.name
    db = MCUDatabase.from_json(tmp_path)
    os.unlink(tmp_path)
    return db


# ---------------------------------------------------------------------------
# Test: _parse_function
# ---------------------------------------------------------------------------


def test_parse_af_function():
    assert _parse_function("USART2_TX") == ("USART2", "TX")


def test_parse_gpio_function():
    assert _parse_function("GPIO_Output") is None
    assert _parse_function("GPIO_Input") is None
    assert _parse_function("GPIO_EXTI") is None


def test_parse_unknown_function():
    assert _parse_function("INVALID") is None


# ---------------------------------------------------------------------------
# Test: no conflicts
# ---------------------------------------------------------------------------


def test_no_conflicts(sample_db):
    hw = _make_mock_hw([
        ("PA2", "USART2_TX"),
        ("PA3", "USART2_RX"),
        ("PB6", "I2C1_SCL"),
        ("PB7", "I2C1_SDA"),
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert errors == []


# ---------------------------------------------------------------------------
# Test: duplicate pin (same function)
# ---------------------------------------------------------------------------


def test_duplicate_pin_same_function(sample_db):
    """Same pin used twice for the same function - should be allowed (not an error)."""
    hw = _make_mock_hw([
        ("PA2", "USART2_TX"),
        ("PA2", "USART2_TX"),  # duplicate, same function
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert errors == []


# ---------------------------------------------------------------------------
# Test: conflicting AF functions
# ---------------------------------------------------------------------------


def test_conflict_different_functions(sample_db):
    """Same pin assigned to two different AF functions -> conflict."""
    hw = _make_mock_hw([
        ("PA2", "USART2_TX"),
        ("PA2", "TIM2_CH2"),
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PinConflictError)
    assert errors[0].pin == "PA2"
    assert "USART2_TX" in str(errors[0])
    assert "TIM2_CH2" in str(errors[0])


# ---------------------------------------------------------------------------
# Test: GPIO does not conflict
# ---------------------------------------------------------------------------


def test_gpio_af_conflict(sample_db):
    """GPIO_Output + AF function on same pin -> conflict (one function per pin)."""
    hw = _make_mock_hw([
        ("PA2", "USART2_TX"),
        ("PA2", "GPIO_Output"),
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PinConflictError)


def test_multiple_gpio_same_pin(sample_db):
    """Two GPIO functions on same pin -> no conflict."""
    hw = _make_mock_hw([
        ("PA0", "GPIO_Output"),
        ("PA0", "GPIO_Output"),
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert errors == []


# ---------------------------------------------------------------------------
# Test: invalid pin
# ---------------------------------------------------------------------------


def test_invalid_pin(sample_db):
    hw = _make_mock_hw([
        ("PZ99", "USART2_TX"),
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], InvalidPinError)


# ---------------------------------------------------------------------------
# Test: unsupported function on pin
# ---------------------------------------------------------------------------


def test_unsupported_function(sample_db):
    """Assign function to pin that doesn't support it."""
    hw = _make_mock_hw([
        ("PB6", "USART2_TX"),  # PB6 supports I2C1_SCL, not USART2_TX
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], UnsupportedFunctionError)


# ---------------------------------------------------------------------------
# Test: re-assigning GPIO -> AF
# ---------------------------------------------------------------------------


def test_gpio_upgrade_to_af(sample_db):
    """GPIO first, then AF on same pin -> conflict (one function per pin)."""
    hw = _make_mock_hw([
        ("PA2", "GPIO_Output"),
        ("PA2", "USART2_TX"),
    ])
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PinConflictError)


# ---------------------------------------------------------------------------
# Test: peripheral pin references (cs_pin / de_pin / ...)
# ---------------------------------------------------------------------------


def test_peripheral_ref_undeclared_pin(sample_db):
    """Peripheral cs_pin not declared in pins -> error (missing GPIO config)."""
    hw = _make_mock_hw([("PA2", "USART2_TX")])
    hw.peripherals = [_make_mock_peri("flash", "SPI_Flash_W25Q32", cs_pin="PB6")]
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PeripheralPinRefError)
    assert "PB6" in str(errors[0])


def test_peripheral_ref_shared_pin(sample_db):
    """Two peripherals referencing the same CS pin -> conflict."""
    hw = _make_mock_hw([("PA2", "USART2_TX"), ("PB6", "GPIO_Output")])
    hw.peripherals = [
        _make_mock_peri("flash", "SPI_Flash_W25Q32", cs_pin="PB6"),
        _make_mock_peri("imu", "SPI_Sensor_MPU6500", cs_pin="PB6"),
    ]
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PinConflictError)
    assert "PB6" in str(errors[0])


def test_peripheral_ref_af_pin(sample_db):
    """Peripheral CS referencing a pin already assigned an AF function -> conflict."""
    hw = _make_mock_hw([("PA2", "USART2_TX")])
    hw.peripherals = [_make_mock_peri("flash", "SPI_Flash_W25Q32", cs_pin="PA2")]
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PinConflictError)


def test_peripheral_ref_ok(sample_db):
    """Valid CS reference (GPIO pin declared in pins) -> no error."""
    hw = _make_mock_hw([("PA2", "USART2_TX"), ("PB6", "GPIO_Output")])
    hw.peripherals = [_make_mock_peri("flash", "SPI_Flash_W25Q32", cs_pin="PB6")]
    errors = validate_pin_conflicts(hw, sample_db)
    assert errors == []


def test_peripheral_ref_via_extra(sample_db):
    """cs_pin inside extra dict is also validated."""
    hw = _make_mock_hw([("PA2", "USART2_TX")])
    hw.peripherals = [_make_mock_peri(
        "flash", "SPI_Flash_W25Q32",
        extra={"chip_select_pin": "PB6"},
    )]
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PeripheralPinRefError)


def test_peripheral_ref_rs485_de_shared_ok(sample_db):
    """UART rs485_de_pin + its paired RS485 de_pin on one pin -> allowed."""
    hw = _make_mock_hw([("PA1", "GPIO_Output")])
    hw.peripherals = [
        _make_mock_peri("usart1", "UART_Serial",
                        extra={"rs485_de_pin": "PA1"}),
        _make_mock_peri("rs485", "RS485",
                        extra={"uart": "usart1", "de_pin": "PA1"}),
    ]
    errors = validate_pin_conflicts(hw, sample_db)
    assert errors == []


def test_peripheral_ref_rs485_de_unpaired_conflict(sample_db):
    """UART + RS485 share DE but RS485 is not linked to that UART -> conflict."""
    hw = _make_mock_hw([("PA1", "GPIO_Output")])
    hw.peripherals = [
        _make_mock_peri("usart1", "UART_Serial",
                        extra={"rs485_de_pin": "PA1"}),
        _make_mock_peri("rs485", "RS485",
                        extra={"uart": "usart2", "de_pin": "PA1"}),
    ]
    errors = validate_pin_conflicts(hw, sample_db)
    assert len(errors) == 1
    assert isinstance(errors[0], PinConflictError)


# ---------------------------------------------------------------------------
# Test: error messages
# ---------------------------------------------------------------------------


def test_conflict_error_message():
    err = PinConflictError("PA2", "USART2_TX", "TIM2_CH1", "UART_TX", "Timer")
    msg = str(err)
    assert "PA2" in msg
    assert "USART2_TX" in msg
    assert "TIM2_CH1" in msg
    assert "UART_TX" in msg
    assert "Timer" in msg


def test_invalid_pin_error_message():
    err = InvalidPinError("PZ99", "USART2_TX", "UART")
    msg = str(err)
    assert "PZ99" in msg
    assert "USART2_TX" in msg


def test_unsupported_function_error_message():
    err = UnsupportedFunctionError("PB6", "USART2_TX", None, ["I2C1_SCL"])
    msg = str(err)
    assert "PB6" in msg
    assert "USART2_TX" in msg
    assert "I2C1_SCL" in msg
