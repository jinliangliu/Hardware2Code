"""Tests for passive component extractor."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from parser.passive_extractor import (
    PassiveExtractor, PassiveConstraints,
    _classify_component, _parse_resistance, _parse_capacitance,
    _parse_frequency, _parse_voltage, _parse_connector_pins,
)


# ---------------------------------------------------------------------------
# Classification tests
# ---------------------------------------------------------------------------

def test_classify_resistor_by_designator():
    assert _classify_component("10k", "R_0805", "R1") == "resistor"


def test_classify_capacitor_by_designator():
    assert _classify_component("100nF", "C_0805", "C1") == "capacitor"


def test_classify_crystal_by_footprint():
    assert _classify_component("8MHz", "Crystal_HC49", "Y1") == "crystal"


def test_classify_connector_by_footprint():
    assert _classify_component("USB", "USB_Micro-B", "J1") == "connector"


def test_classify_regulator_by_footprint():
    assert _classify_component("3.3V", "SOT-223_LDO", "U2") == "regulator"


def test_classify_unknown():
    assert _classify_component("xyz", "BGA_999", "Z99") == "unknown"


def test_classify_by_value_pattern():
    """Resistor-like value should classify even with ambiguous designator."""
    assert _classify_component("4.7k", "Unknown", "X1") == "resistor"


# ---------------------------------------------------------------------------
# Value parsing tests
# ---------------------------------------------------------------------------

def test_parse_resistance_10k():
    ohms, _ = _parse_resistance("10k")
    assert ohms == 10000.0


def test_parse_resistance_100R():
    ohms, _ = _parse_resistance("100R")
    assert ohms == 100.0


def test_parse_resistance_4k7():
    ohms, _ = _parse_resistance("4.7k")
    assert ohms == 4700.0


def test_parse_resistance_1M():
    ohms, _ = _parse_resistance("1M")
    assert ohms == 1e6


def test_parse_capacitance_100nF():
    farad, _ = _parse_capacitance("100nF")
    assert abs(farad - 100e-9) < 1e-15


def test_parse_capacitance_10uF():
    farad, _ = _parse_capacitance("10uF")
    assert abs(farad - 10e-6) < 1e-15


def test_parse_capacitance_22pF():
    farad, _ = _parse_capacitance("22pF")
    assert abs(farad - 22e-12) < 1e-15


def test_parse_capacitance_with_voltage():
    farad, voltage = _parse_capacitance("10uF 16V")
    assert abs(farad - 10e-6) < 1e-15
    assert abs(voltage - 16.0) < 1e-9


def test_parse_frequency_8MHz():
    hz = _parse_frequency("8MHz")
    assert hz == 8e6


def test_parse_frequency_32_768kHz():
    hz = _parse_frequency("32.768kHz")
    assert hz == 32768.0


def test_parse_voltage_3v3():
    v = _parse_voltage("3.3V")
    assert v == 3.3


def test_parse_connector_1x4():
    pins = _parse_connector_pins("1x4", "")
    assert pins == 4


def test_parse_connector_2x10():
    pins = _parse_connector_pins("2x10", "")
    assert pins == 20


def test_parse_connector_pin_suffix():
    pins = _parse_connector_pins("20pin", "")
    assert pins == 20


# ---------------------------------------------------------------------------
# Full extraction tests
# ---------------------------------------------------------------------------

SAMPLE_BOM_ROWS = [
    {"Designator": "R1", "Value": "10k", "Footprint": "R_0805"},
    {"Designator": "R2", "Value": "4.7k", "Footprint": "R_0805"},
    {"Designator": "R3", "Value": "100R", "Footprint": "R_0805"},
    {"Designator": "C1", "Value": "100nF", "Footprint": "C_0805"},
    {"Designator": "C2", "Value": "10uF", "Footprint": "C_1206"},
    {"Designator": "C3", "Value": "22pF", "Footprint": "C_0805"},
    {"Designator": "Y1", "Value": "8MHz", "Footprint": "Crystal_HC49"},
    {"Designator": "Y2", "Value": "32.768kHz", "Footprint": "Crystal_SMD_3215"},
    {"Designator": "J1", "Value": "USB", "Footprint": "USB_Micro-B"},
    {"Designator": "J2", "Value": "2x5", "Footprint": "PinHeader_2x05"},
    {"Designator": "U2", "Value": "3.3V", "Footprint": "SOT-223_LDO"},
]


def test_extract_pull_resistors():
    ext = PassiveExtractor()
    result = ext.extract(SAMPLE_BOM_ROWS)
    assert len(result.pull_resistors) >= 1
    pull_values = [r.resistance_ohms for r in result.pull_resistors]
    assert 10000.0 in pull_values  # 10k
    assert 4700.0 in pull_values   # 4.7k


def test_extract_decoupling_caps():
    ext = PassiveExtractor()
    result = ext.extract(SAMPLE_BOM_ROWS)
    assert len(result.decoupling_caps) >= 1
    cap_values = [c.capacitance_farad for c in result.decoupling_caps]
    assert any(abs(v - 100e-9) < 1e-15 for v in cap_values)  # 100nF
    assert any(abs(v - 10e-6) < 1e-15 for v in cap_values)    # 10uF


def test_extract_crystals():
    ext = PassiveExtractor()
    result = ext.extract(SAMPLE_BOM_ROWS)
    assert len(result.crystals) >= 2
    freqs = [c.frequency_hz for c in result.crystals]
    assert 8e6 in freqs
    assert 32768.0 in freqs


def test_extract_connectors():
    ext = PassiveExtractor()
    result = ext.extract(SAMPLE_BOM_ROWS)
    assert len(result.connectors) >= 1


def test_extract_regulators():
    ext = PassiveExtractor()
    result = ext.extract(SAMPLE_BOM_ROWS)
    assert len(result.power_regulators) >= 1
    reg = result.power_regulators[0]
    assert reg.output_voltage == 3.3


def test_100r_not_pull_resistor():
    """100R is too low to be a pull-up/down resistor."""
    ext = PassiveExtractor()
    result = ext.extract(SAMPLE_BOM_ROWS)
    pull_refs = [r.designator for r in result.pull_resistors]
    assert "R3" not in pull_refs, "100R should NOT be a pull resistor"


def test_summary_string():
    ext = PassiveExtractor()
    result = ext.extract(SAMPLE_BOM_ROWS)
    s = result.summary()
    assert "Regulators:" in s
    assert "Decoupling caps:" in s
    assert "Crystals" in s


def test_empty_rows():
    ext = PassiveExtractor()
    result = ext.extract([])
    assert result.summary()  # should not crash


def test_empty_cells():
    ext = PassiveExtractor()
    result = ext.extract([
        {"Designator": "", "Value": "", "Footprint": ""},
        {"Designator": "R1", "Value": "", "Footprint": ""},
    ])
    assert result.summary()
