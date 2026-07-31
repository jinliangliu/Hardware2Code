"""Tests for PinAllocator."""

import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from generator.allocators.pin_allocator import (
    AllocationError,
    PinAllocator,
    _PERIPHERAL_SIGNALS,
    _SWD_PINS,
)
from generator.mcu_database import MCUDatabase


# ---------------------------------------------------------------------------
# Sample MCU data fixture (subset of a real MCU for fast tests)
# ---------------------------------------------------------------------------

SAMPLE_JSON = {
    "name": "TestMCU",
    "family": "Test",
    "peripherals": [
        {
            "name": "USART1",
            "pins": [
                {"pin": "PA9",  "signal": "TX", "af": 1},
                {"pin": "PA10", "signal": "RX", "af": 1},
                {"pin": "PB6",  "signal": "TX", "af": 0},
                {"pin": "PB7",  "signal": "RX", "af": 0},
            ],
        },
        {
            "name": "USART2",
            "pins": [
                {"pin": "PA2",  "signal": "TX", "af": 1},
                {"pin": "PA3",  "signal": "RX", "af": 1},
                {"pin": "PA14", "signal": "TX", "af": 1},  # SWD pin
                {"pin": "PA15", "signal": "RX", "af": 1},
            ],
        },
        {
            "name": "I2C1",
            "pins": [
                {"pin": "PB6", "signal": "SCL", "af": 1},
                {"pin": "PB7", "signal": "SDA", "af": 1},
                {"pin": "PB8", "signal": "SCL", "af": 1},
                {"pin": "PB9", "signal": "SDA", "af": 1},
            ],
        },
        {
            "name": "SPI1",
            "pins": [
                {"pin": "PA5", "signal": "SCK",  "af": 0},
                {"pin": "PA6", "signal": "MISO", "af": 0},
                {"pin": "PA7", "signal": "MOSI", "af": 0},
                {"pin": "PA4", "signal": "NSS",  "af": 0},
                {"pin": "PB3", "signal": "SCK",  "af": 0},
                {"pin": "PB4", "signal": "MISO", "af": 0},
                {"pin": "PB5", "signal": "MOSI", "af": 0},
            ],
        },
        {
            "name": "TIM2",
            "pins": [
                {"pin": "PA0", "signal": "CH1", "af": 1},
                {"pin": "PA1", "signal": "CH2", "af": 1},
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


@pytest.fixture
def alloc(sample_db):
    return PinAllocator(sample_db)


# ---------------------------------------------------------------------------
# Test: single pin allocation
# ---------------------------------------------------------------------------


def test_allocate_returns_pin(alloc):
    pin = alloc.allocate("USART2", "TX")
    # PA2 is the priority hint for USART2_TX
    assert pin == "PA2"


def test_allocate_excludes_swd(alloc):
    """PA14 is SWD; USART2_TX on PA14 should never be auto-selected."""
    pin = alloc.allocate("USART2", "TX")
    assert pin != "PA14"  # SWD pin should be excluded


def test_allocate_exhausted_raises(alloc):
    """After all USART2_TX candidates are used, allocation should fail."""
    alloc.allocate("USART2", "TX")  # takes PA2
    # PA14 is SWD (excluded), so only PA2 was available
    with pytest.raises(AllocationError):
        alloc.allocate("USART2", "TX")


def test_pre_allocate_prevents_auto(alloc):
    """Pre-allocating a pin should make it unavailable for auto-allocation."""
    alloc.pre_allocate("PA2", "USART2", "TX")
    # Now PA2 is taken; PA14 is SWD excluded, so nothing left
    with pytest.raises(AllocationError):
        alloc.allocate("USART2", "TX")


def test_is_allocated(alloc):
    assert alloc.is_allocated("PA2") is False
    alloc.allocate("USART2", "TX")
    assert alloc.is_allocated("PA2") is True


def test_is_allocated_case_insensitive(alloc):
    alloc.pre_allocate("PA2", "USART2", "TX")
    assert alloc.is_allocated("pa2") is True


def test_release(alloc):
    alloc.allocate("USART2", "TX")
    assert alloc.is_allocated("PA2")
    alloc.release("PA2")
    assert not alloc.is_allocated("PA2")
    # Should be allocatable again
    pin = alloc.allocate("USART2", "TX")
    assert pin == "PA2"


def test_allocated_pins_property(alloc):
    alloc.pre_allocate("PA2", "USART2", "TX")
    alloc.allocate("I2C1", "SCL")
    ap = alloc.allocated_pins
    assert "PA2" in ap
    assert ap["PA2"] == ("USART2", "TX", 1)


# ---------------------------------------------------------------------------
# Test: bus (atomic multi-pin) allocation
# ---------------------------------------------------------------------------


def test_allocate_bus_success(alloc):
    result = alloc.allocate_bus("SPI1", ["SCK", "MISO", "MOSI", "NSS"])
    assert len(result) == 4
    # Should prefer same port (PA for SPI1)
    ports = {p[1] for p in result.values()}
    assert ports <= {"A"}, f"All SPI1 pins should be on port A, got {ports}"


def test_allocate_bus_same_port(alloc):
    """Bus allocation should prefer pins on the same GPIO port."""
    result = alloc.allocate_bus("I2C1", ["SCL", "SDA"])
    ports = {p[1] for p in result.values()}
    assert len(ports) == 1, f"I2C1 SCL/SDA should be on same port, got {ports}"


def test_allocate_bus_partial_rollback(alloc):
    """If one signal fails, all previous bus allocations should roll back."""
    # Pre-allocate NSS to make it unavailable for the bus allocation
    alloc.pre_allocate("PA4", "SPI1", "NSS")
    allocated_before = dict(alloc._allocated)

    # SPI1 has no NSS on port B — only PA4, so NSS will fail
    with pytest.raises(AllocationError):
        alloc.allocate_bus("SPI1", ["SCK", "MISO", "MOSI", "NSS"])

    # Verify rollback: SCK/MISO/MOSI should not have been committed
    assert alloc._allocated == allocated_before, (
        "Allocations should have been rolled back on bus failure"
    )


def test_allocate_bus_empty_signals(alloc):
    """Empty signal list should succeed trivially."""
    result = alloc.allocate_bus("USART2", [])
    assert result == {}


# ---------------------------------------------------------------------------
# Test: priority hints
# ---------------------------------------------------------------------------


def test_priority_hint_usart2(alloc):
    """PA2 is the priority hint for USART2_TX."""
    pin = alloc.allocate("USART2", "TX")
    assert pin == "PA2"


def test_priority_hint_i2c1(alloc):
    """PB6 is the priority hint for I2C1_SCL."""
    pin = alloc.allocate("I2C1", "SCL")
    assert pin == "PB6"


# ---------------------------------------------------------------------------
# Test: allocate_all with HardwareModel mock
# ---------------------------------------------------------------------------


def _make_mock_pin(pin_id, function, label=None, af=0):
    p = MagicMock()
    p.id = pin_id
    p.function = function
    p.label = label
    p.af = af
    return p


def _make_mock_peripheral(name, ptype, interface=None, bus=None, uart=None):
    p = MagicMock()
    p.name = name
    p.type = ptype
    p.interface = interface
    p.bus = bus
    p.uart = uart
    return p


def _make_mock_hw(pins, peripherals):
    hw = MagicMock()
    hw.pins = pins
    hw.peripherals = peripherals
    return hw


def test_allocate_all_pre_allocates_existing(alloc):
    """Pins already in the YAML should be pre-allocated before auto-assignment."""
    pins = [_make_mock_pin("PA2", "USART2_TX")]
    periphs = []
    hw = _make_mock_hw(pins, periphs)
    alloc.allocate_all(hw)
    assert alloc.is_allocated("PA2")


def test_allocate_all_fills_missing(alloc):
    """Missing pins should be auto-allocated."""
    pins = [
        _make_mock_pin("PA2", "USART2_TX"),
        _make_mock_pin("PA3", "USART2_RX"),
    ]
    periphs = [
        _make_mock_peripheral("i2c1", "I2C_EEPROM", bus="I2C1"),
    ]
    hw = _make_mock_hw(pins, periphs)
    new_pins = alloc.allocate_all(hw)

    assert len(new_pins) >= 2  # SCL + SDA
    funcs = {p["function"] for p in new_pins}
    assert "I2C1_SCL" in funcs
    assert "I2C1_SDA" in funcs


def test_allocate_all_skips_when_all_assigned(alloc):
    """When all pins are already assigned, no new pins should be generated."""
    pins = [
        _make_mock_pin("PB6", "I2C1_SCL"),
        _make_mock_pin("PB7", "I2C1_SDA"),
    ]
    periphs = [
        _make_mock_peripheral("i2c1", "I2C_EEPROM", bus="I2C1"),
    ]
    hw = _make_mock_hw(pins, periphs)
    new_pins = alloc.allocate_all(hw)
    assert new_pins == []


def test_allocate_all_skips_unresolvable_peripheral(alloc):
    """Peripherals without interface/bus/uart should be skipped."""
    periphs = [
        _make_mock_peripheral("unknown", "Internal_ADC"),  # no interface/bus
    ]
    hw = _make_mock_hw([], periphs)
    new_pins = alloc.allocate_all(hw)
    # ADC has no interface/bus/uart set, and "unknown" doesn't match a
    # peripheral pattern — should be skipped gracefully
    assert isinstance(new_pins, list)


def test_allocate_all_spi_gets_4_pins(alloc):
    """SPI_Flash should auto-allocate 4 pins (SCK, MISO, MOSI, NSS)."""
    pins = []
    periphs = [
        _make_mock_peripheral("spi_flash", "SPI_Flash_W25Q32", bus="SPI1"),
    ]
    hw = _make_mock_hw(pins, periphs)
    new_pins = alloc.allocate_all(hw)
    assert len(new_pins) == 4
    signals = {p["function"].rsplit("_", 1)[1] for p in new_pins}
    assert signals == {"SCK", "MISO", "MOSI", "NSS"}


def test_allocate_all_uart_gets_2_pins(alloc):
    """UART_Serial should auto-allocate 2 pins (TX, RX)."""
    pins = []
    periphs = [
        _make_mock_peripheral("uart2", "UART_Serial", interface="USART2"),
    ]
    hw = _make_mock_hw(pins, periphs)
    new_pins = alloc.allocate_all(hw)
    assert len(new_pins) == 2


def test_allocate_all_skips_when_generic_pins_exist(alloc):
    """Peripheral with generic pin names (I2C_SCL for I2C1) should be skipped."""
    pins = [
        _make_mock_pin("PB6", "I2C_SCL"),
        _make_mock_pin("PB7", "I2C_SDA"),
    ]
    periphs = [
        _make_mock_peripheral("eeprom", "I2C_EEPROM", bus="I2C1"),
    ]
    hw = _make_mock_hw(pins, periphs)
    new_pins = alloc.allocate_all(hw)
    # I2C1 pins are already defined with generic names → should skip
    assert new_pins == [], (
        f"Should skip I2C1 (manual pins exist), got: {new_pins}"
    )


def test_allocate_all_skips_spi_with_generic_pins(alloc):
    """Peripheral with generic SPI pin names (SPI_SCK for SPI1) should be skipped."""
    pins = [
        _make_mock_pin("PA5", "SPI_SCK"),
        _make_mock_pin("PA6", "SPI_MISO"),
    ]
    periphs = [
        _make_mock_peripheral("flash", "SPI_Flash_W25Q32", bus="SPI1"),
    ]
    hw = _make_mock_hw(pins, periphs)
    new_pins = alloc.allocate_all(hw)
    assert new_pins == []


# ---------------------------------------------------------------------------
# Test: _has_manual_pins
# ---------------------------------------------------------------------------


def test_has_manual_pins_exact_match(alloc):
    """Exact match: USART2 appears in USART2_TX."""
    pins = [_make_mock_pin("PA2", "USART2_TX")]
    assert alloc._has_manual_pins(pins, "USART2") is True


def test_has_manual_pins_generic_match(alloc):
    """Generic match: I2C_SCL matches I2C1 (prefix I2C)."""
    pins = [_make_mock_pin("PB6", "I2C_SCL")]
    assert alloc._has_manual_pins(pins, "I2C1") is True


def test_has_manual_pins_no_match(alloc):
    """No match: I2C_SCL doesn't match USART1."""
    pins = [_make_mock_pin("PB6", "I2C_SCL")]
    assert alloc._has_manual_pins(pins, "USART1") is False


def test_has_manual_pins_empty_pins(alloc):
    """Empty pin list returns False."""
    assert alloc._has_manual_pins([], "I2C1") is False


# ---------------------------------------------------------------------------
# Test: _resolve_peripheral_name
# ---------------------------------------------------------------------------


def test_resolve_uses_interface(alloc):
    peri = _make_mock_peripheral("uart_debug", "UART_Serial", interface="USART2")
    assert alloc._resolve_peripheral_name(peri) == "USART2"


def test_resolve_uses_bus(alloc):
    peri = _make_mock_peripheral("eeprom", "I2C_EEPROM", bus="I2C1")
    assert alloc._resolve_peripheral_name(peri) == "I2C1"


def test_resolve_fallback_name(alloc):
    peri = MagicMock()
    peri.name = "USART3"
    peri.interface = None
    peri.bus = None
    peri.uart = None
    assert alloc._resolve_peripheral_name(peri) == "USART3"


def test_resolve_returns_none_for_unknown(alloc):
    peri = MagicMock()
    peri.name = "weird_device"
    peri.interface = None
    peri.bus = None
    peri.uart = None
    assert alloc._resolve_peripheral_name(peri) is None


# ---------------------------------------------------------------------------
# Test: _parse_function_str
# ---------------------------------------------------------------------------


def test_parse_af_function(alloc):
    assert alloc._parse_function_str("USART2_TX") == ("USART2", "TX")
    assert alloc._parse_function_str("I2C1_SCL") == ("I2C1", "SCL")
    assert alloc._parse_function_str("TIM2_CH1") == ("TIM2", "CH1")


def test_parse_gpio_returns_none(alloc):
    assert alloc._parse_function_str("GPIO_Output") is None
    assert alloc._parse_function_str("GPIO_Input") is None
    assert alloc._parse_function_str("GPIO_EXTI") is None


# ---------------------------------------------------------------------------
# Test: _find_assigned_signals
# ---------------------------------------------------------------------------


def test_find_assigned_signals(alloc):
    alloc.pre_allocate("PA2", "USART2", "TX")
    alloc.pre_allocate("PB6", "I2C1", "SCL")

    result = alloc._find_assigned_signals("USART2", ["TX", "RX"])
    assert result == {"TX"}

    result = alloc._find_assigned_signals("I2C1", ["SCL", "SDA"])
    assert result == {"SCL"}


# ---------------------------------------------------------------------------
# Test: constants
# ---------------------------------------------------------------------------


def test_peripheral_signals_coverage():
    """Ensure all known peripheral types have signal mappings."""
    from generator.schemas.hardware import VALID_PERIPHERAL_TYPES
    missing = VALID_PERIPHERAL_TYPES - set(_PERIPHERAL_SIGNALS.keys()) - {
        "Internal_RTC", "Internal_CLI", "Internal_IWDG",
        "Internal_TempSensor",
        "Protocol_Modbus", "Protocol_MQTT",
    }
    assert missing == set(), f"Missing signal mapping for: {missing}"


def test_swd_pins_excluded():
    """PA13 and PA14 must be in the SWD exclusion set."""
    assert "PA13" in _SWD_PINS
    assert "PA14" in _SWD_PINS
