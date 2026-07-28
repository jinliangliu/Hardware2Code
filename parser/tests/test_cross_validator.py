"""Tests for netlist-YAML cross-validator."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from parser.cross_validator import CrossValidator, CrossReport

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

NETLIST_YAML = """\
mcu:
  part: STM32G0B1RET6
  core_clock_mhz: 64
pins:
- id: PA5
  function: SPI1_SCK
  label: SPI1_SCK
  af: 0
- id: PA6
  function: SPI1_MISO
  label: SPI1_MISO
  af: 0
- id: PA7
  function: SPI1_MOSI
  label: SPI1_MOSI
  af: 0
- id: PB0
  function: GPIO_Output
  label: SPI1_NSS
  active_level: low
  af: 0
- id: PB6
  function: I2C1_SCL
  label: I2C1_SCL
  af: 1
- id: PB7
  function: I2C1_SDA
  label: I2C1_SDA
  af: 1
peripherals:
- name: w25q32jvssiq
  type: SPI_Flash_W25Q32
  bus: SPI1
  cs_pin: PB0
- name: mpu6050
  type: I2C_Sensor_MPU6050
  bus: I2C1
  address: 0x68
app_tasks:
- name: w25q32jvssiq_task
  priority: 3
  stack_size: 512
- name: mpu6050_task
  priority: 4
  stack_size: 512
"""


# ---------------------------------------------------------------------------
# Tests: exact match
# ---------------------------------------------------------------------------

def test_exact_match_no_issues():
    """Identical netlist and YAML should produce zero issues."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, NETLIST_YAML)
    assert len(report.issues) == 0, f"Expected 0 issues, got {report.issues}"
    assert not report.has_errors


def test_mcu_match():
    """MCU part should be extracted correctly."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, NETLIST_YAML)
    assert report.netlist_mcu == "STM32G0B1RET6"
    assert report.yaml_mcu == "STM32G0B1RET6"


# ---------------------------------------------------------------------------
# Tests: MCU mismatch
# ---------------------------------------------------------------------------

def test_mcu_mismatch():
    """Different MCU parts should produce MCU_MISMATCH error."""
    hw_with_different_mcu = NETLIST_YAML.replace(
        "STM32G0B1RET6", "STM32F407VGT6"
    )
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, hw_with_different_mcu)
    errors = [i for i in report.issues if i.code == "MCU_MISMATCH"]
    assert len(errors) == 1
    assert errors[0].severity == "error"


# ---------------------------------------------------------------------------
# Tests: pin conflicts
# ---------------------------------------------------------------------------

HW_WITH_PIN_CONFLICT = """\
mcu:
  part: STM32G0B1RET6
  core_clock_mhz: 64
pins:
- id: PA5
  function: USART1_TX
  label: USART1_TX
  af: 1
- id: PB6
  function: I2C1_SCL
  label: I2C1_SCL
  af: 1
- id: PB7
  function: I2C1_SDA
  label: I2C1_SDA
  af: 1
peripherals: []
"""


def test_pin_conflict_detected():
    """PA5 assigned SPI1_SCK in netlist but USART1_TX in YAML."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, HW_WITH_PIN_CONFLICT)
    conflicts = [i for i in report.issues if i.code == "PIN_CONFLICT"]
    assert len(conflicts) == 1
    assert conflicts[0].pin == "PA5"
    assert conflicts[0].severity == "error"


# ---------------------------------------------------------------------------
# Tests: missing pins
# ---------------------------------------------------------------------------

HW_WITH_MISSING_PINS = """\
mcu:
  part: STM32G0B1RET6
  core_clock_mhz: 64
pins:
- id: PB6
  function: I2C1_SCL
  label: I2C1_SCL
  af: 1
peripherals: []
"""


def test_missing_pins_detected():
    """Pins in netlist but absent from YAML should be flagged."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, HW_WITH_MISSING_PINS)
    missing = [i for i in report.issues if i.code == "PIN_MISSING"]
    assert len(missing) >= 1, f"Expected at least 1 missing pin, got {missing}"
    missing_pins = [m.pin for m in missing]
    assert "PA6" in missing_pins or "PA7" in missing_pins


# ---------------------------------------------------------------------------
# Tests: extra pins
# ---------------------------------------------------------------------------

HW_WITH_EXTRA_PINS = NETLIST_YAML + """\
- id: PC13
  function: GPIO_Input
  label: USER_BTN
  pull: up
  af: 0
"""


def test_extra_gpio_pins_ignored():
    """Extra GPIO pins in YAML (not in netlist) should not raise errors."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, HW_WITH_EXTRA_PINS)
    extras = [i for i in report.issues if i.code == "PIN_EXTRA"]
    assert len(extras) == 0, \
        f"Extra GPIO pins should be ignored, but got: {extras}"


def test_extra_af_pins_warned():
    """Extra AF pins in YAML should produce warnings."""
    import yaml
    import copy
    hw_doc = yaml.safe_load(NETLIST_YAML)
    hw_doc = copy.deepcopy(hw_doc)
    hw_doc.setdefault("pins", []).append({
        "id": "PC10", "function": "USART4_TX",
        "label": "DEBUG_UART", "af": 1,
    })
    hw_with_extra_af = yaml.dump(hw_doc, default_flow_style=False)
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, hw_with_extra_af)
    extras = [i for i in report.issues if i.code == "PIN_EXTRA"]
    assert len(extras) == 1
    assert extras[0].pin == "PC10"


# ---------------------------------------------------------------------------
# Tests: peripheral mismatches
# ---------------------------------------------------------------------------

HW_WITH_PERIPH_MISMATCH = """\
mcu:
  part: STM32G0B1RET6
  core_clock_mhz: 64
pins:
- id: PB6
  function: I2C1_SCL
  label: I2C1_SCL
  af: 1
- id: PB7
  function: I2C1_SDA
  label: I2C1_SDA
  af: 1
peripherals:
- name: mpu6050
  type: I2C_EEPROM
  bus: I2C1
  address: 0x50
"""


def test_peripheral_type_mismatch():
    """Peripheral type differs between netlist and YAML."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, HW_WITH_PERIPH_MISMATCH)
    mismatches = [i for i in report.issues if i.code == "PERIPH_MISMATCH"]
    assert len(mismatches) == 1
    assert mismatches[0].severity == "error"


# ---------------------------------------------------------------------------
# Tests: pin refinement (info)
# ---------------------------------------------------------------------------

def test_pin_refined():
    """Netlist says GPIO_Output, YAML refines to specific AF — info only."""
    hw_refined = NETLIST_YAML.replace(
        "GPIO_Output\n  label: SPI1_NSS",
        "SPI1_NSS\n  label: SPI1_NSS"
    )
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, hw_refined)
    refined = [i for i in report.issues if i.code == "PIN_REFINED"]
    assert len(refined) == 1
    assert refined[0].severity == "info"


# ---------------------------------------------------------------------------
# Tests: empty inputs
# ---------------------------------------------------------------------------

def test_empty_yamls_no_error():
    """Empty YAML docs should not crash."""
    v = CrossValidator()
    report = v.validate("", "mcu: {part: STM32G0B1RET6}")
    assert report.netlist_mcu is None
    assert report.yaml_mcu == "STM32G0B1RET6"


# ---------------------------------------------------------------------------
# Tests: report formatting
# ---------------------------------------------------------------------------

def test_report_string_format():
    """CrossReport.__str__ includes error/warning counts."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, HW_WITH_PIN_CONFLICT)
    s = str(report)
    assert "Cross-Validation Report" in s
    assert "error(s)" in s or "1 error" in s


def test_report_has_errors():
    """has_errors returns True when errors exist."""
    v = CrossValidator()
    report = v.validate(NETLIST_YAML, HW_WITH_PIN_CONFLICT)
    assert report.has_errors
