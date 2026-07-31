"""Tests for generator/builders/ package.

Tests GPIOBuilder pin calculation, Registry auto-discovery,
I2C timing calculation, and SPI prescaler computation.
"""

from generator.builders.gpio_builder import GpioBuilder, _compute_pin_entry
from generator.builders.i2c_builder import _calc_i2c_timing
from generator.builders.spi_builder import _calc_spi_prescaler
from generator.builders.registry import get_builder, get_all_builders


# =========================================================================
# GPIO Builder tests
# =========================================================================

def test_compute_pin_entry_output():
    """GPIO_Output pin computes correct mode/pull/speed"""
    entry = _compute_pin_entry(
        {"id": "PA5", "function": "GPIO_Output", "pull": "up"},
        "GPIO_Output"
    )
    assert entry["pin_name"] == "GPIO_PIN_5"
    assert entry["pin_num"] == 5
    assert entry["mode"] == "GPIO_MODE_OUTPUT_PP"
    assert entry["pull"] == "GPIO_PULLUP"
    assert entry["speed"] == "GPIO_SPEED_FREQ_LOW"
    assert entry["alt"] == 0


def test_compute_pin_entry_input():
    """GPIO_Input pin computes correct mode"""
    entry = _compute_pin_entry(
        {"id": "PA0", "function": "GPIO_Input", "pull": "down"},
        "GPIO_Input"
    )
    assert entry["mode"] == "GPIO_MODE_INPUT"
    assert entry["pull"] == "GPIO_PULLDOWN"


def test_compute_pin_entry_af_i2c():
    """I2C SCL pin computes AF mode with alt number"""
    entry = _compute_pin_entry(
        {"id": "PB6", "function": "I2C1_SCL", "af": 1},
        "I2C1_SCL"
    )
    assert entry["mode"] == "GPIO_MODE_AF_PP"
    assert entry["alt"] == 1


def test_compute_pin_entry_af_spi():
    """SPI SCK pin computes AF mode"""
    entry = _compute_pin_entry(
        {"id": "PA5", "function": "SPI1_SCK", "af": 0},
        "SPI1_SCK"
    )
    assert entry["mode"] == "GPIO_MODE_AF_PP"
    assert entry["alt"] == 0


def test_compute_pin_entry_adc():
    """ADC_IN pin computes analog mode"""
    entry = _compute_pin_entry(
        {"id": "PA1", "function": "ADC_IN1"},
        "ADC_IN1"
    )
    assert entry["mode"] == "GPIO_MODE_ANALOG"


# =========================================================================
# GPIO build_pin_groups tests
# =========================================================================

def test_build_pin_groups_single_port():
    """Multiple pins on same port are grouped together"""
    pins = [
        {"id": "PA5", "function": "GPIO_Output"},
        {"id": "PA6", "function": "GPIO_Output"},
    ]
    groups = GpioBuilder.build_pin_groups(pins)
    assert len(groups) == 1
    assert groups[0]["port"] == "A"
    assert groups[0]["port_name"] == "GPIOA"
    assert len(groups[0]["pins"]) == 2


def test_build_pin_groups_multi_port():
    """Pins on different ports are separated"""
    pins = [
        {"id": "PA5", "function": "GPIO_Output"},
        {"id": "PC13", "function": "GPIO_Output"},
        {"id": "PB0", "function": "GPIO_Input"},
    ]
    groups = GpioBuilder.build_pin_groups(pins)
    ports = sorted(g["port"] for g in groups)
    assert ports == ["A", "B", "C"]
    assert len(groups) == 3


def test_build_pin_groups_empty():
    """Empty pin list returns empty groups"""
    groups = GpioBuilder.build_pin_groups([])
    assert groups == []


# =========================================================================
# I2C timing calculation tests
# =========================================================================

def test_calc_i2c_timing_100khz_16mhz():
    """100 kHz standard mode at 16 MHz I2C clock"""
    timing = _calc_i2c_timing(16_000_000, 100_000)
    assert timing == 0x00000F13


def test_calc_i2c_timing_400khz_16mhz():
    """400 kHz fast mode at 16 MHz I2C clock"""
    timing = _calc_i2c_timing(16_000_000, 400_000)
    assert timing == 0x00000307


def test_calc_i2c_timing_100khz_64mhz():
    """100 kHz standard mode at 64 MHz I2C clock"""
    timing = _calc_i2c_timing(64_000_000, 100_000)
    assert timing == 0x00303D5B


def test_calc_i2c_timing_fallback():
    """Unknown clock/target combination uses default"""
    timing = _calc_i2c_timing(32_000_000, 200_000)
    # Fallback to 100kHz @ 16MHz
    assert timing == 0x00000F13


# =========================================================================
# SPI prescaler calculation tests
# =========================================================================

def test_calc_spi_prescaler_1mhz():
    """Target 1 MHz SPI at 16 MHz clock -> prescaler 16"""
    prescaler = _calc_spi_prescaler(16_000_000, 1_000_000)
    assert prescaler == 16


def test_calc_spi_prescaler_500khz():
    """Target 500 kHz at 16 MHz -> prescaler 32"""
    prescaler = _calc_spi_prescaler(16_000_000, 500_000)
    assert prescaler == 32


def test_calc_spi_prescaler_8mhz():
    """Target 8 MHz at 16 MHz -> prescaler 2"""
    prescaler = _calc_spi_prescaler(16_000_000, 8_000_000)
    assert prescaler == 2


def test_calc_spi_prescaler_slow():
    """Very slow target speed uses max prescaler"""
    prescaler = _calc_spi_prescaler(16_000_000, 10_000)
    assert prescaler == 256


# =========================================================================
# Registry tests
# =========================================================================

def test_registry_has_i2c_builder():
    """Registry auto-discovers I2C builder by type string"""
    builder_cls = get_builder({"type": "I2C_Sensor_MPU6050"})
    assert builder_cls is not None
    assert hasattr(builder_cls, "calculate")


def test_registry_has_spi_builder():
    """Registry auto-discovers SPI builder"""
    builder_cls = get_builder({"type": "SPI_Flash_W25Q32"})
    assert builder_cls is not None
    assert hasattr(builder_cls, "calculate")


def test_registry_has_uart_builder():
    """Registry auto-discovers UART builder"""
    builder_cls = get_builder({"type": "UART_Serial"})
    assert builder_cls is not None


def test_registry_unknown_type_returns_none():
    """Unknown peripheral type returns None"""
    builder_cls = get_builder({"type": "NonExistentType"})
    assert builder_cls is None


def test_registry_all_builders():
    """get_all_builders returns at least the builders we registered"""
    all_builders = get_all_builders()
    builder_types = {b.peripheral_type for b in all_builders if b.peripheral_type}
    assert "I2C_Sensor_MPU6050" in builder_types
    assert "SPI_Flash_W25Q32" in builder_types
    assert "UART_Serial" in builder_types
    assert "RS485" in builder_types
    assert "Cellular_4G" in builder_types


if __name__ == "__main__":
    # GPIO
    test_compute_pin_entry_output()
    test_compute_pin_entry_input()
    test_compute_pin_entry_af_i2c()
    test_compute_pin_entry_af_spi()
    test_compute_pin_entry_adc()
    test_build_pin_groups_single_port()
    test_build_pin_groups_multi_port()
    test_build_pin_groups_empty()
    # I2C
    test_calc_i2c_timing_100khz_16mhz()
    test_calc_i2c_timing_400khz_16mhz()
    test_calc_i2c_timing_100khz_64mhz()
    test_calc_i2c_timing_fallback()
    # SPI
    test_calc_spi_prescaler_1mhz()
    test_calc_spi_prescaler_500khz()
    test_calc_spi_prescaler_8mhz()
    test_calc_spi_prescaler_slow()
    # Registry
    test_registry_has_i2c_builder()
    test_registry_has_spi_builder()
    test_registry_has_uart_builder()
    test_registry_unknown_type_returns_none()
    test_registry_all_builders()
    print("All builder tests passed.")
