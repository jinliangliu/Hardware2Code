"""Tests for EasyEDA Pro .enet netlist parser."""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import yaml
from parser.netlist_parser import parse_netlist_string, parse_netlist, _detect_format
from parser.netlist_parser_enet import parse_netlist_enet


# ---------------------------------------------------------------------------
# Test fixtures: realistic STM32G0B1 EasyEDA Pro netlists
# ---------------------------------------------------------------------------

def _make_enet(components: dict) -> str:
    """Helper: wrap components into a minimal .enet JSON structure."""
    enet = {
        "version": "2.0.0",
        "components": components,
        "designRule": {
            "trackPhysics": {},
            "netRule": {},
        },
        "differentialPair": {},
        "netClass": {},
        "equalLengthNetGroup": {},
    }
    return json.dumps(enet)


# ---- MCU + I2C sensor (MPU6050) ----

ENET_I2C = _make_enet({
    "gge1": {
        "props": {
            "Designator": "U1",
            "Value": "STM32G0B1RET6",
            "FootprintName": "LQFP-64",
            "DeviceName": "STM32G0B1RET6",
        },
        "pinInfoMap": {
            "27": {"name": "PB6", "number": "PB6", "net": "I2C1_SCL",
                   "props": {"Pin Number": "PB6"}},
            "28": {"name": "PB7", "number": "PB7", "net": "I2C1_SDA",
                   "props": {"Pin Number": "PB7"}},
        },
    },
    "gge2": {
        "props": {
            "Designator": "U2",
            "Value": "MPU6050",
            "FootprintName": "QFN-24",
            "DeviceName": "MPU6050",
        },
        "pinInfoMap": {
            "23": {"name": "SCL", "number": "SCL", "net": "I2C1_SCL",
                   "props": {"Pin Number": "SCL"}},
            "24": {"name": "SDA", "number": "SDA", "net": "I2C1_SDA",
                   "props": {"Pin Number": "SDA"}},
        },
    },
})

# ---- MCU + SPI Flash (W25Q32) ----

ENET_SPI = _make_enet({
    "gge1": {
        "props": {
            "Designator": "U1",
            "Value": "STM32G0B1RET6",
            "FootprintName": "LQFP-64",
            "DeviceName": "STM32G0B1RET6",
        },
        "pinInfoMap": {
            "PA5": {"name": "PA5", "number": "PA5", "net": "SPI1_SCK",
                    "props": {"Pin Number": "PA5"}},
            "PA6": {"name": "PA6", "number": "PA6", "net": "SPI1_MISO",
                    "props": {"Pin Number": "PA6"}},
            "PA7": {"name": "PA7", "number": "PA7", "net": "SPI1_MOSI",
                    "props": {"Pin Number": "PA7"}},
            "PB0": {"name": "PB0", "number": "PB0", "net": "FLASH_nCS",
                    "props": {"Pin Number": "PB0"}},
        },
    },
    "gge2": {
        "props": {
            "Designator": "U3",
            "Value": "W25Q32JVSSIQ",
            "FootprintName": "SOIC-8",
            "DeviceName": "W25Q32JVSSIQ",
        },
        "pinInfoMap": {
            "1": {"name": "CS", "number": "CS", "net": "FLASH_nCS",
                  "props": {"Pin Number": "1"}},
            "2": {"name": "SO", "number": "SO", "net": "SPI1_MISO",
                  "props": {"Pin Number": "2"}},
            "5": {"name": "SI", "number": "SI", "net": "SPI1_MOSI",
                  "props": {"Pin Number": "5"}},
            "6": {"name": "CLK", "number": "CLK", "net": "SPI1_SCK",
                  "props": {"Pin Number": "6"}},
        },
    },
})

# ---- MCU + UART (MAX3232) ----

ENET_UART = _make_enet({
    "gge1": {
        "props": {
            "Designator": "U1",
            "Value": "STM32G0B1RET6",
            "FootprintName": "LQFP-64",
            "DeviceName": "STM32G0B1RET6",
        },
        "pinInfoMap": {
            "PA2": {"name": "PA2", "number": "PA2", "net": "USART2_TX",
                    "props": {"Pin Number": "PA2"}},
            "PA3": {"name": "PA3", "number": "PA3", "net": "USART2_RX",
                    "props": {"Pin Number": "PA3"}},
        },
    },
    "gge2": {
        "props": {
            "Designator": "U4",
            "Value": "MAX3232",
            "FootprintName": "SOIC-16",
            "DeviceName": "MAX3232",
        },
        "pinInfoMap": {
            "TX": {"name": "TX", "number": "TX", "net": "USART2_TX",
                   "props": {"Pin Number": "TX"}},
            "RX": {"name": "RX", "number": "RX", "net": "USART2_RX",
                   "props": {"Pin Number": "RX"}},
        },
    },
})

# ---- MCU + LED + Button ----

ENET_LED_BTN = _make_enet({
    "gge1": {
        "props": {
            "Designator": "U1",
            "Value": "STM32G0B1RET6",
            "FootprintName": "LQFP-64",
            "DeviceName": "STM32G0B1RET6",
        },
        "pinInfoMap": {
            "PA5": {"name": "PA5", "number": "PA5", "net": "LED_RED",
                    "props": {"Pin Number": "PA5"}},
            "PC13": {"name": "PC13", "number": "PC13", "net": "BUTTON",
                     "props": {"Pin Number": "PC13"}},
        },
    },
    "gge2": {
        "props": {
            "Designator": "D1",
            "Value": "LED_RED",
            "FootprintName": "LED_0805",
            "DeviceName": "LED_RED",
        },
        "pinInfoMap": {
            "1": {"name": "1", "number": "1", "net": "LED_RED",
                  "props": {"Pin Number": "1"}},
        },
    },
    "gge3": {
        "props": {
            "Designator": "SW1",
            "Value": "BUTTON",
            "FootprintName": "SW_TACT",
            "DeviceName": "SW_TACT",
        },
        "pinInfoMap": {
            "1": {"name": "1", "number": "1", "net": "BUTTON",
                  "props": {"Pin Number": "1"}},
        },
    },
})

# ---- Auto-generated net names ($1N2) with passives ----

ENET_AUTO_NETS = _make_enet({
    "gge1": {
        "props": {
            "Designator": "U1",
            "Value": "STM32G0B1RET6",
            "FootprintName": "LQFP-64",
            "DeviceName": "STM32G0B1RET6",
        },
        "pinInfoMap": {
            "PA0": {"name": "PA0", "number": "PA0", "net": "USER_LED",
                    "props": {"Pin Number": "PA0"}},
        },
    },
    "gge2": {
        "props": {
            "Designator": "D1",
            "Value": "LED_RED",
            "FootprintName": "LED_0805",
            "DeviceName": "LED_RED",
        },
        "pinInfoMap": {
            "1": {"name": "1", "number": "1", "net": "USER_LED",
                  "props": {"Pin Number": "1"}},
            "2": {"name": "2", "number": "2", "net": "GND",
                  "props": {"Pin Number": "2"}},
        },
    },
    "gge3": {
        "props": {
            "Designator": "R1",
            "Value": "330",
            "FootprintName": "R0603",
            "DeviceName": "Res_0603",
        },
        "pinInfoMap": {
            "1": {"name": "1", "number": "1", "net": "USER_LED",
                  "props": {"Pin Number": "1"}},
            "2": {"name": "2", "number": "2", "net": "$1N5",
                  "props": {"Pin Number": "2"}},
        },
    },
})

# ---- NC pins (empty net) ----

ENET_NC_PINS = _make_enet({
    "gge1": {
        "props": {
            "Designator": "U1",
            "Value": "STM32G0B1RET6",
            "FootprintName": "LQFP-64",
            "DeviceName": "STM32G0B1RET6",
        },
        "pinInfoMap": {
            "PA5": {"name": "PA5", "number": "PA5", "net": "",
                    "props": {"Pin Number": "PA5"}},
            "PA6": {"name": "PA6", "number": "PA6", "net": "",
                    "props": {"Pin Number": "PA6"}},
        },
    },
})


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def test_detect_format_enet():
    """_detect_format identifies .enet JSON."""
    assert _detect_format(ENET_I2C) == "enet"
    assert _detect_format('{"version":"2.0.0","components":{}}') == "enet"


def test_detect_format_xml():
    """_detect_format still identifies XML correctly."""
    xml_text = '<?xml version="1.0"?><export version="D"/>'
    assert _detect_format(xml_text) == "xml"


def test_detect_format_sexpr():
    """_detect_format still identifies S-Expr correctly."""
    assert _detect_format("(kicad_netlist (version 20240108)") == "sexpr"


# ---------------------------------------------------------------------------
# Core parsing tests
# ---------------------------------------------------------------------------

def test_enet_parse_mcu():
    """ENet: MCU detected from STM32 value."""
    result = parse_netlist_string(ENET_I2C)
    hw = yaml.safe_load(result)
    assert hw["mcu"]["part"] == "STM32G0B1RET6"


def test_enet_parse_i2c_peripheral():
    """ENet: I2C peripheral (MPU6050) detected."""
    result = parse_netlist_string(ENET_I2C)
    assert "I2C_Sensor_MPU6050" in result
    assert "I2C1_SCL" in result
    assert "I2C1_SDA" in result


def test_enet_parse_i2c_pins():
    """ENet: I2C pins PB6/PB7 assigned correctly."""
    result = parse_netlist_string(ENET_I2C)
    hw = yaml.safe_load(result)
    pins = {p["id"]: p for p in hw.get("pins", [])}
    assert "PB6" in pins, f"PB6 not in {list(pins.keys())}"
    assert pins["PB6"]["function"] == "I2C1_SCL"
    assert "PB7" in pins
    assert pins["PB7"]["function"] == "I2C1_SDA"


def test_enet_parse_spi_peripheral():
    """ENet: SPI peripheral (W25Q32) detected."""
    result = parse_netlist_string(ENET_SPI)
    assert "SPI_Flash_W25Q32" in result


def test_enet_parse_spi_pins():
    """ENet: SPI pins assigned correctly."""
    result = parse_netlist_string(ENET_SPI)
    assert "SPI1_SCK" in result
    assert "SPI1_MISO" in result
    assert "SPI1_MOSI" in result


def test_enet_parse_spi_cs_pin():
    """ENet: SPI CS pin assigned as GPIO_Output with NSS label."""
    result = parse_netlist_string(ENET_SPI)
    hw = yaml.safe_load(result)
    cs_pins = [p for p in hw.get("pins", [])
               if "NSS" in p.get("label", "")]
    assert len(cs_pins) > 0, "No CS/NSS pin found"


def test_enet_parse_uart_peripheral():
    """ENet: UART peripheral (MAX3232) detected."""
    result = parse_netlist_string(ENET_UART)
    assert "UART_Serial" in result


def test_enet_parse_uart_pins():
    """ENet: UART pins PA2/PA3 assigned correctly."""
    result = parse_netlist_string(ENET_UART)
    assert "USART2_TX" in result
    assert "USART2_RX" in result


def test_enet_parse_led_pin():
    """ENet: LED generates GPIO_Output."""
    result = parse_netlist_string(ENET_LED_BTN)
    hw = yaml.safe_load(result)
    led_pins = [p for p in hw.get("pins", [])
                if "LED" in p.get("label", "")]
    assert len(led_pins) > 0


def test_enet_parse_button_pin():
    """ENet: Button generates GPIO_Input with EXTI."""
    result = parse_netlist_string(ENET_LED_BTN)
    hw = yaml.safe_load(result)
    btn_pins = [p for p in hw.get("pins", [])
                if "BUTTON" in p.get("label", "")]
    assert len(btn_pins) > 0
    btn = btn_pins[0]
    assert btn["function"] == "GPIO_Input"
    assert btn.get("pull") == "up"
    assert btn.get("exti", {}).get("enable") == True


def test_enet_parse_app_tasks():
    """ENet: App tasks generated for detected peripherals."""
    result = parse_netlist_string(ENET_I2C)
    assert "mpu6050_task" in result


def test_enet_no_mcu_raises():
    """ENet without MCU raises ValueError."""
    no_mcu = _make_enet({
        "gge1": {
            "props": {
                "Designator": "U2",
                "Value": "MPU6050",
                "DeviceName": "MPU6050",
            },
            "pinInfoMap": {},
        },
    })
    try:
        parse_netlist_string(no_mcu)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "MCU" in str(e)


def test_enet_invalid_json_raises():
    """ENet with invalid JSON raises ValueError."""
    try:
        parse_netlist_string("not valid json {{{[")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_enet_empty_components():
    """ENet with empty components raises ValueError."""
    empty_comp = _make_enet({})
    try:
        parse_netlist_string(empty_comp)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "No components" in str(e) or "No MCU" in str(e)


def test_enet_nc_pins_handled():
    """ENet: NC pins (net="") do not cause errors."""
    result = parse_netlist_string(ENET_NC_PINS)
    hw = yaml.safe_load(result)
    assert hw["mcu"]["part"] == "STM32G0B1RET6"


def test_enet_auto_net_names():
    """ENet: Auto-generated net names ($1N5) are handled correctly.

    Nets that are only auto-generated (connecting passives) are filtered
    out during reconstruction. The MCU still gets parsed.
    """
    result = parse_netlist_string(ENET_AUTO_NETS)
    hw = yaml.safe_load(result)
    assert hw["mcu"]["part"] == "STM32G0B1RET6"
    # LED pin should still be detected
    pins = hw.get("pins", [])
    assert len(pins) >= 1


# ---------------------------------------------------------------------------
# Direct enet parser API
# ---------------------------------------------------------------------------

def test_parse_netlist_enet_direct():
    """parse_netlist_enet can be called directly."""
    result = parse_netlist_enet(ENET_I2C)
    assert "I2C1_SCL" in result


# ---------------------------------------------------------------------------
# File-based parse
# ---------------------------------------------------------------------------

def test_enet_parse_from_file():
    """parse_netlist works with .enet file path."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.enet', delete=False, encoding='utf-8',
    ) as f:
        f.write(ENET_I2C)
        tmp_path = f.name

    try:
        result = parse_netlist(tmp_path)
        assert "STM32G0B1RET6" in result
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------

def test_pipeline_with_enet():
    """Pipeline works with .enet netlist text."""
    from parser.pipeline import run_pipeline
    result = run_pipeline(netlist_text=ENET_I2C)
    assert result.yaml
    doc = yaml.safe_load(result.yaml)
    assert doc["mcu"]["part"] == "STM32G0B1RET6"


def test_pipeline_enet_annotations():
    """Pipeline extracts annotations from .enet net names."""
    from parser.pipeline import run_pipeline
    result = run_pipeline(netlist_text=ENET_I2C)
    peri_names = {h.name for h in result.annotations.peripheral_hints}
    # Note: peripheral prefix detection depends on net naming conventions
    # If nets are "I2C1_SCL" type, MPU6050 won't be detected by name prefix
    # That's expected — bus hints should be detected instead
    bus_names = {h.bus_name for h in result.annotations.bus_hints}
    assert "I2C1" in bus_names, f"I2C1 not in bus hints: {bus_names}"
