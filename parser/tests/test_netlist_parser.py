"""Tests for KiCad netlist parser."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from parser.netlist_parser import parse_netlist_string


SAMPLE_NETLIST = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
    </comp>
  </components>
  <nets>
    <net code="1" name="Net-(U1-PA5)">
      <node ref="U1" pin="PA5"/>
      <node ref="D1" pin="1"/>
    </net>
  </nets>
</export>"""

SAMPLE_I2C_NETLIST = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <design>
    <source>hardware.sch</source>
    <date>2024-01-01</date>
    <tool>Eeschema (7.0.0)</tool>
  </design>
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
      <footprint>Package_QFP:LQFP-64_10x10mm_P0.5mm</footprint>
    </comp>
    <comp ref="U2">
      <value>MPU6050</value>
      <footprint>Sensor_Motion:MPU-6050</footprint>
    </comp>
  </components>
  <nets>
    <net code="1" name="Net-(U1-PB6)">
      <node ref="U1" pin="PB6"/>
      <node ref="U2" pin="SCL"/>
    </net>
    <net code="2" name="Net-(U1-PB7)">
      <node ref="U1" pin="PB7"/>
      <node ref="U2" pin="SDA"/>
    </net>
  </nets>
</export>"""


def test_parse_mcu():
    """Parse MCU from netlist."""
    result = parse_netlist_string(SAMPLE_NETLIST)
    assert "STM32G0B1RET6" in result, "MCU part not found in YAML"
    assert "mcu:" in result, "mcu section missing"


def test_parse_mcu_in_section():
    """MCU should be in mcu.part section."""
    result = parse_netlist_string(SAMPLE_I2C_NETLIST)
    # Load YAML and check structure
    import yaml
    hw = yaml.safe_load(result)
    assert hw["mcu"]["part"] == "STM32G0B1RET6", "Wrong MCU part"


def test_parse_i2c_peripheral():
    """I2C peripheral (MPU6050) is detected from net connections."""
    result = parse_netlist_string(SAMPLE_I2C_NETLIST)
    assert "MPU6050" in result, "MPU6050 not found in YAML"
    assert "I2C1" in result, "I2C1 bus not found in YAML"
    assert "I2C_Sensor_MPU6050" in result, "Peripheral type not found"


def test_parse_i2c_pins():
    """I2C pins (PB6/PB7) should be assigned I2C1_SCL/I2C1_SDA."""
    result = parse_netlist_string(SAMPLE_I2C_NETLIST)
    assert "I2C1_SCL" in result, "SCL not assigned"
    assert "I2C1_SDA" in result, "SDA not assigned"
    assert "PB6" in result, "PB6 not in output"
    assert "PB7" in result, "PB7 not in output"


def test_parse_app_tasks_generated():
    """App tasks should be generated for each peripheral."""
    result = parse_netlist_string(SAMPLE_I2C_NETLIST)
    assert "mpu6050_task" in result, "mpu6050 task not generated"


def test_no_mcu_raises():
    """Parsing a netlist without an MCU should raise ValueError."""
    no_mcu_xml = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U2">
      <value>MPU6050</value>
    </comp>
  </components>
  <nets/>
</export>"""
    try:
        parse_netlist_string(no_mcu_xml)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "MCU" in str(e), f"Error message should mention MCU: {e}"


# ---------- SPI tests ----------

SPI_NETLIST = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
    </comp>
    <comp ref="U3">
      <value>W25Q32JVSSIQ</value>
    </comp>
  </components>
  <nets>
    <net code="1" name="Net-(U1-PA5)">
      <node ref="U1" pin="PA5"/>
      <node ref="U3" pin="CLK"/>
    </net>
    <net code="2" name="Net-(U1-PA6)">
      <node ref="U1" pin="PA6"/>
      <node ref="U3" pin="SO"/>
    </net>
    <net code="3" name="Net-(U1-PA7)">
      <node ref="U1" pin="PA7"/>
      <node ref="U3" pin="SI"/>
    </net>
    <net code="4" name="Net-(U1-PB0)">
      <node ref="U1" pin="PB0"/>
      <node ref="U3" pin="CS"/>
    </net>
  </nets>
</export>"""


def test_parse_spi_peripheral():
    """SPI Flash peripheral is detected from net connections."""
    result = parse_netlist_string(SPI_NETLIST)
    assert "SPI_Flash_W25Q32" in result, "SPI Flash not found"


def test_parse_spi_pins():
    """SPI pins should be assigned correct functions."""
    result = parse_netlist_string(SPI_NETLIST)
    assert "SPI1_SCK" in result, "SCK not assigned"
    assert "SPI1_MISO" in result, "MISO not assigned"
    assert "SPI1_MOSI" in result, "MOSI not assigned"


def test_parse_spi_cs_pin():
    """SPI CS pin should be assigned GPIO_Output."""
    result = parse_netlist_string(SPI_NETLIST)
    import yaml
    hw = yaml.safe_load(result)
    cs_pins = [p for p in hw.get("pins", []) if "NSS" in p.get("label", "")]
    assert len(cs_pins) > 0, "No CS/NSS pin found"
    assert cs_pins[0]["function"] == "GPIO_Output"


# ---------- UART tests ----------

UART_NETLIST = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
    </comp>
    <comp ref="U4">
      <value>MAX3232</value>
    </comp>
  </components>
  <nets>
    <net code="1" name="Net-(U1-PA2)">
      <node ref="U1" pin="PA2"/>
      <node ref="U4" pin="TX"/>
    </net>
    <net code="2" name="Net-(U1-PA3)">
      <node ref="U1" pin="PA3"/>
      <node ref="U4" pin="RX"/>
    </net>
  </nets>
</export>"""


def test_parse_uart_peripheral():
    """UART peripheral is detected from net connections."""
    result = parse_netlist_string(UART_NETLIST)
    assert "UART_Serial" in result, "UART_Serial not found"


def test_parse_uart_pins():
    """UART pins should be assigned USART functions."""
    result = parse_netlist_string(UART_NETLIST)
    assert "USART2_TX" in result, "USART2_TX not assigned"
    assert "USART2_RX" in result, "USART2_RX not assigned"


# ---------- LED / Button tests ----------

LED_BTN_NETLIST = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
    </comp>
    <comp ref="D1">
      <value>LED_RED</value>
    </comp>
    <comp ref="SW1">
      <value>BUTTON</value>
    </comp>
  </components>
  <nets>
    <net code="1" name="Net-(U1-PA5)">
      <node ref="U1" pin="PA5"/>
      <node ref="D1" pin="1"/>
    </net>
    <net code="2" name="Net-(U1-PC13)">
      <node ref="U1" pin="PC13"/>
      <node ref="SW1" pin="1"/>
    </net>
  </nets>
</export>"""


def test_parse_led_pin():
    """LED component generates GPIO_Output with LED label."""
    result = parse_netlist_string(LED_BTN_NETLIST)
    import yaml
    hw = yaml.safe_load(result)
    led_pins = [p for p in hw.get("pins", []) if "LED" in p.get("label", "")]
    assert len(led_pins) > 0, "No LED pins found"


def test_parse_button_pin():
    """Button component generates GPIO_Input with EXTI."""
    result = parse_netlist_string(LED_BTN_NETLIST)
    import yaml
    hw = yaml.safe_load(result)
    btn_pins = [p for p in hw.get("pins", []) if "BUTTON" in p.get("label", "")]
    assert len(btn_pins) > 0, "No button pins found"
    btn = btn_pins[0]
    assert btn["function"] == "GPIO_Input"
    assert btn.get("pull") == "up"
    assert btn.get("exti", {}).get("enable") == True


# ---------- Edge cases ----------

EMPTY_NETLIST = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
    </comp>
  </components>
</export>"""


def test_empty_nets():
    """Netlist with no nets section still parses MCU."""
    result = parse_netlist_string(EMPTY_NETLIST)
    assert "STM32G0B1RET6" in result


# ---------- Unknown / edge components ----------

UNKNOWN_NETLIST = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
    </comp>
    <comp ref="R1">
      <value>10k resistor</value>
    </comp>
  </components>
  <nets>
    <net code="1" name="Net-(U1-PB1)">
      <node ref="U1" pin="PB1"/>
      <node ref="R1" pin="1"/>
    </net>
  </nets>
</export>"""


def test_unknown_component():
    """Unknown component gets GPIO_Output fallback."""
    result = parse_netlist_string(UNKNOWN_NETLIST)
    import yaml
    hw = yaml.safe_load(result)
    pins = hw.get("pins", [])
    assert len(pins) > 0, "Should have at least one pin"
    assert any("NET_" in p.get("label", "") for p in pins), "Unknown net not labeled"


# ---------- File-based parse ----------

def test_parse_netlist_from_file():
    """parse_netlist from a file path works."""
    import tempfile
    from parser.netlist_parser import parse_netlist

    with tempfile.NamedTemporaryFile(mode='w', suffix='.net',
                                       delete=False, encoding='utf-8') as f:
        f.write(SAMPLE_NETLIST)
        tmp_path = f.name

    try:
        result = parse_netlist(tmp_path)
        assert "STM32G0B1RET6" in result
    finally:
        os.unlink(tmp_path)


def test_parse_netlist_file_not_found():
    """parse_netlist with missing file raises FileNotFoundError."""
    from parser.netlist_parser import parse_netlist
    try:
        parse_netlist("nonexistent_xyz_file.net")
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


# ---------- Pin-to-bus lookup ----------

def test_pin_to_bus_i2c():
    """PB6 on I2C returns I2C1_SCL with AF1"""
    from parser.netlist_parser import _pin_to_bus_info
    func, af, bus = _pin_to_bus_info("PB6", "I2C")
    assert func == "I2C1_SCL"
    assert af == 1
    assert bus == "I2C1"


def test_pin_to_bus_gpio():
    """GPIO interface returns GPIO_Output"""
    from parser.netlist_parser import _pin_to_bus_info
    func, af, bus = _pin_to_bus_info("PA5", "GPIO")
    assert func == "GPIO_Output"
    assert af == 0


def test_pin_to_bus_unknown_pin():
    """Unknown pin falls back to interface-based name"""
    from parser.netlist_parser import _pin_to_bus_info
    func, af, bus = _pin_to_bus_info("PX0", "SPI")
    assert "SPI" in func
