"""Tests for schematic annotator."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from parser.schematic_annotator import SchematicAnnotator, AnnotationHints


SAMPLE_NETS = [
    "MPU6050_SCL",
    "MPU6050_SDA",
    "MPU6050_INT",
    "W25Q32_CS",
    "W25Q32_CLK", "W25Q32_MISO", "W25Q32_MOSI",
    "USART2_TX", "USART2_RX",
    "nRST",
    "3V3",
    "GND",
    "LED_STATUS",
    "BUTTON_USER",
    "SPI1_SCK", "SPI1_MISO", "SPI1_MOSI", "SPI1_NSS",
    "I2C1_SCL", "I2C1_SDA",
    "BOOT0",
    "SWDIO", "SWCLK",
]


# ---------------------------------------------------------------------------
# Bus hints
# ---------------------------------------------------------------------------

def test_bus_hints_spi1():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    spi1 = [h for h in hints.bus_hints if h.bus_name == "SPI1"]
    assert len(spi1) == 1
    assert "SCK" in spi1[0].signals
    assert "MISO" in spi1[0].signals
    assert "MOSI" in spi1[0].signals


def test_bus_hints_i2c1():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    i2c1 = [h for h in hints.bus_hints if h.bus_name == "I2C1"]
    assert len(i2c1) == 1
    assert "SCL" in i2c1[0].signals
    assert "SDA" in i2c1[0].signals


def test_bus_hints_usart2():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    usart = [h for h in hints.bus_hints if h.bus_name == "UART2"]
    assert len(usart) == 1
    assert "TX" in usart[0].signals
    assert "RX" in usart[0].signals


def test_bus_hints_no_number_defaults():
    """Net with I2C_SCL (no number) should default to I2C1."""
    ann = SchematicAnnotator()
    hints = ann.extract(["I2C_SCL", "I2C_SDA"])
    i2c1 = [h for h in hints.bus_hints if h.bus_name == "I2C1"]
    assert len(i2c1) == 1


def test_bus_hints_swd():
    """SWDIO/SWCLK should be detected as SWD bus."""
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    swd = [h for h in hints.bus_hints if h.bus_type == "SWD"]
    assert len(swd) >= 1


# ---------------------------------------------------------------------------
# Peripheral hints
# ---------------------------------------------------------------------------

def test_peripheral_mpu6050():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    mpu = [h for h in hints.peripheral_hints if h.name == "mpu6050"]
    assert len(mpu) == 1
    assert mpu[0].interface == "I2C"


def test_peripheral_w25q32():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    flash = [h for h in hints.peripheral_hints if h.name.startswith("w25q")]
    assert len(flash) >= 1
    assert flash[0].interface == "SPI"


def test_peripheral_led():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    led = [h for h in hints.peripheral_hints if h.name.startswith("led")]
    assert len(led) >= 1


def test_peripheral_button():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    btn = [h for h in hints.peripheral_hints if h.name.startswith("button")]
    assert len(btn) >= 1


# ---------------------------------------------------------------------------
# Power hints
# ---------------------------------------------------------------------------

def test_power_hints_3v3():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    p3v3 = [h for h in hints.power_hints if h.domain == "3V3"]
    assert len(p3v3) == 1
    assert p3v3[0].voltage == 3.3


def test_power_hints_gnd():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    gnd = [h for h in hints.power_hints if h.domain == "GND"]
    assert len(gnd) == 1


# ---------------------------------------------------------------------------
# Signal role hints
# ---------------------------------------------------------------------------

def test_signal_role_nrst():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    assert "nRST" in hints.signal_role_hints


def test_signal_role_boot0():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    assert "BOOT0" in hints.signal_role_hints
    assert hints.signal_role_hints["BOOT0"] == "boot"


# ---------------------------------------------------------------------------
# Summary and edge cases
# ---------------------------------------------------------------------------

def test_summary_string():
    ann = SchematicAnnotator()
    hints = ann.extract(SAMPLE_NETS)
    s = hints.summary()
    assert "Bus hints" in s
    assert "Peripheral groupings" in s
    assert "Power domains" in s
    assert "Signal roles" in s


def test_empty_nets():
    ann = SchematicAnnotator()
    hints = ann.extract([])
    assert hints.summary()
    assert len(hints.bus_hints) == 0


def test_no_matches():
    """Random net names should not crash."""
    ann = SchematicAnnotator()
    hints = ann.extract(["XYZ_ABC", "FOO_BAR_123"])
    assert hints.summary()
