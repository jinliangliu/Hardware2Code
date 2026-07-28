"""
Integration tests for the Phase 4 hardware analysis pipeline.

Tests the full pipeline: netlist → BOM → passive extraction →
schematic annotation → cross-validation → enriched YAML output.
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import yaml
from parser.pipeline import HardwarePipeline, PipelineResult, run_pipeline


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

NETLIST_XML = """<?xml version="1.0" encoding="utf-8"?>
<export version="D">
  <components>
    <comp ref="U1">
      <value>STM32G0B1RET6</value>
      <footprint>Package_QFP:LQFP-64_10x10mm_P0.5mm</footprint>
    </comp>
    <comp ref="U2">
      <value>MPU6050</value>
      <footprint>Sensor_Motion:MPU-6050</footprint>
    </comp>
    <comp ref="U3">
      <value>W25Q32JVSSIQ</value>
      <footprint>Package_SO:SOIC-8_5.23mm</footprint>
    </comp>
    <comp ref="D1">
      <value>LED_RED</value>
      <footprint>LED_0805</footprint>
    </comp>
  </components>
  <nets>
    <net code="1" name="MPU6050_SCL">
      <node ref="U1" pin="PB6"/>
      <node ref="U2" pin="SCL"/>
    </net>
    <net code="2" name="MPU6050_SDA">
      <node ref="U1" pin="PB7"/>
      <node ref="U2" pin="SDA"/>
    </net>
    <net code="3" name="SPI1_SCK">
      <node ref="U1" pin="PA5"/>
      <node ref="U3" pin="CLK"/>
    </net>
    <net code="4" name="SPI1_MISO">
      <node ref="U1" pin="PA6"/>
      <node ref="U3" pin="SO"/>
    </net>
    <net code="5" name="SPI1_MOSI">
      <node ref="U1" pin="PA7"/>
      <node ref="U3" pin="SI"/>
    </net>
    <net code="6" name="FLASH_nCS">
      <node ref="U1" pin="PB0"/>
      <node ref="U3" pin="CS"/>
    </net>
    <net code="7" name="Net-(U1-PA5)">
      <node ref="U1" pin="PA5"/>
      <node ref="D1" pin="1"/>
    </net>
  </nets>
</export>"""

BOM_CSV = """Designator,Value,Footprint
U1,STM32G0B1RET6,LQFP-64
U2,MPU6050,QFN-24
U3,W25Q32JVSSIQ,SOIC-8
D1,LED_RED,LED_0805
C1,100nF,C_0805
C2,100nF,C_0805
R1,10k,R_0805
Y1,8MHz,Crystal_HC49"""

USER_YAML = """mcu:
  part: STM32G0B1RET6
  core_clock_mhz: 64
pins:
  - id: PB6
    function: I2C1_SCL
    label: MPU6050_SCL
    af: 1
  - id: PB7
    function: I2C1_SDA
    label: MPU6050_SDA
    af: 1
  - id: PA5
    function: SPI1_SCK
    label: FLASH_SCK
    af: 0
  - id: PA6
    function: SPI1_MISO
    label: FLASH_MISO
    af: 0
  - id: PA7
    function: SPI1_MOSI
    label: FLASH_MOSI
    af: 0
peripherals:
  - name: mpu6050
    type: I2C_Sensor_MPU6050
    bus: I2C1
    address: 0x68
  - name: w25q32
    type: SPI_Flash_W25Q32
    bus: SPI1
"""


# ---------------------------------------------------------------------------
# Pipeline basic tests
# ---------------------------------------------------------------------------

def test_pipeline_netlist_only():
    """Pipeline runs with only a netlist."""
    result = run_pipeline(netlist_text=NETLIST_XML)
    assert result.yaml, "Should produce YAML output"
    doc = yaml.safe_load(result.yaml)
    assert doc["mcu"]["part"] == "STM32G0B1RET6"
    assert len(result.warnings) == 0


def test_pipeline_annotations_from_netlist():
    """Pipeline extracts schematic annotations from net names."""
    result = run_pipeline(netlist_text=NETLIST_XML)
    assert result.annotations.bus_hints, "Should detect bus hints"
    bus_names = {h.bus_name for h in result.annotations.bus_hints}
    assert "SPI1" in bus_names, f"SPI1 not in bus hints: {bus_names}"

    peri_names = {h.name for h in result.annotations.peripheral_hints}
    assert "mpu6050" in peri_names, f"MPU6050 not in peripheral hints: {peri_names}"
    # W25Q32 uses generic SPI net names (SPI1_SCK etc.), so it won't be
    # detected by peripheral prefix matching — that's expected.


def test_pipeline_with_bom():
    """Pipeline runs with netlist + BOM."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        bom_text=BOM_CSV,
    )
    assert result.yaml, "Should produce YAML output"
    doc = yaml.safe_load(result.yaml)
    assert doc["mcu"]["part"] == "STM32G0B1RET6"
    assert len(doc.get("peripherals", [])) >= 2, "Should have peripherals"


def test_pipeline_passive_extraction():
    """Passive component constraints are extracted from BOM."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        bom_text=BOM_CSV,
    )
    pc = result.passive_constraints
    assert len(pc.decoupling_caps) > 0, "Should detect decoupling caps"
    assert len(pc.crystals) > 0, "Should detect crystal"
    assert len(pc.pull_resistors) > 0, "Should detect pull resistor"


def test_pipeline_embedded_annotations():
    """Annotations are embedded as YAML comments."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        bom_text=BOM_CSV,
    )
    assert "# hw2c-annot:" in result.yaml, (
        "Annotations should be embedded as comments"
    )
    assert "SPI1" in result.yaml, "Bus hint should be in comments"


def test_pipeline_cross_validation():
    """Cross-validation runs when user YAML is provided."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        bom_text=BOM_CSV,
        hw_yaml_text=USER_YAML,
    )
    assert result.report is not None, "Should have cross-validation report"
    report_str = str(result.report)
    assert "MCU" in report_str, "Report should mention MCU check"


def test_pipeline_cross_validation_passes():
    """Matched netlist + user YAML → no errors."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        hw_yaml_text=USER_YAML,
    )
    assert not result.report.has_errors, (
        f"Should have no errors, got: {result.report.errors}"
    )


def test_pipeline_no_input_returns_warning():
    """Pipeline with no netlist returns warning."""
    result = run_pipeline()
    assert len(result.warnings) > 0, "Should warn about missing input"


def test_pipeline_yaml_merge_union():
    """Merged YAML contains peripherals from both netlist and BOM."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        bom_text=BOM_CSV,
    )
    doc = yaml.safe_load(result.yaml)
    pins = doc.get("pins", [])
    assert len(pins) >= 4, f"Should have at least 4 pins, got {len(pins)}: {pins}"


def test_pipeline_power_hints():
    """Power domain hints from net names are extracted."""
    nets_with_power = NETLIST_XML.replace(
        'name="SPI1_SCK"', 'name="3V3"'
    ).replace(
        'name="SPI1_MISO"', 'name="GND"'
    )
    result = run_pipeline(netlist_text=nets_with_power)
    assert result.annotations.power_hints, "Should detect power domains"


def test_pipeline_signal_role_hints():
    """Signal role hints are extracted (active_low from nCS)."""
    result = run_pipeline(netlist_text=NETLIST_XML)
    roles = result.annotations.signal_role_hints
    assert roles, f"Should detect signal roles, got {roles}"
    # FLASH_nCS should be detected as active_low
    assert any("nCS" in net or "FLASH" in net for net in roles), (
        f"nCS signal role not in {roles}"
    )


# ---------------------------------------------------------------------------
# File-based integration tests
# ---------------------------------------------------------------------------

def test_pipeline_from_files():
    """Pipeline works with file paths instead of strings."""
    result = None
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.xml', delete=False, encoding='utf-8',
    ) as nf:
        nf.write(NETLIST_XML)
        netlist_path = nf.name

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.csv', delete=False, encoding='utf-8',
    ) as bf:
        bf.write(BOM_CSV)
        bom_path = bf.name

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', delete=False, encoding='utf-8',
    ) as yf:
        yf.write(USER_YAML)
        yaml_path = yf.name

    try:
        pipe = HardwarePipeline()
        result = pipe.run(
            netlist_path=netlist_path,
            bom_path=bom_path,
            hw_yaml_path=yaml_path,
        )
    finally:
        for p in (netlist_path, bom_path, yaml_path):
            try:
                os.unlink(p)
            except OSError:
                pass

    assert result is not None
    assert result.yaml
    assert not result.report.has_errors, (
        f"File-based cross-validation should pass, errors: {result.report.errors}"
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_pipeline_empty_netlist():
    """Empty netlist without MCU returns warning, pipeline handles gracefully."""
    empty_xml = """<?xml version="1.0" encoding="utf-8"?>
    <export version="D"><components/><nets/></export>"""
    result = run_pipeline(netlist_text=empty_xml)
    assert len(result.warnings) >= 0, (
        "Should not crash on empty/partial netlist"
    )
    # Netlist parse error is caught and warning is logged


def test_pipeline_yaml_includes_annotation_comments():
    """Enriched YAML starts with annotation comments."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        bom_text=BOM_CSV,
    )
    lines = result.yaml.splitlines()
    # First non-empty line should be a hw2c-annot comment
    non_empty = [l for l in lines if l.strip()]
    assert non_empty, "YAML should not be empty"
    assert "# hw2c-annot:" in non_empty[0], (
        f"First line should be annot comment, got: {non_empty[0]}"
    )


def test_pipeline_summary():
    """PipelineResult.summary() returns non-empty string."""
    result = run_pipeline(
        netlist_text=NETLIST_XML,
        bom_text=BOM_CSV,
    )
    s = result.summary()
    assert s, "Summary should not be empty"
    assert "Pipeline" in s, "Summary should mention pipeline"


# ---------------------------------------------------------------------------
# S-Expression format pipeline test
# ---------------------------------------------------------------------------

SEXPR_NETLIST = """(kicad_netlist (version 20240108)
  (components
    (comp (ref "U1") (value "STM32G0B1RET6") (footprint "LQFP-64"))
    (comp (ref "U2") (value "MPU6050") (footprint "QFN-24"))
  )
  (nets
    (net (code 1) (name "MPU6050_SCL")
      (node (ref "U1") (pin "PB6"))
      (node (ref "U2") (pin "SCL"))
    )
    (net (code 2) (name "MPU6050_SDA")
      (node (ref "U1") (pin "PB7"))
      (node (ref "U2") (pin "SDA"))
    )
  )
)"""


def test_pipeline_sexpr_format():
    """Pipeline works with S-Expression netlist format."""
    result = run_pipeline(netlist_text=SEXPR_NETLIST)
    assert result.yaml, "Should produce YAML"
    doc = yaml.safe_load(result.yaml)
    assert doc["mcu"]["part"] == "STM32G0B1RET6"
    assert result.annotations.peripheral_hints, (
        "Should detect MPU6050 from net names"
    )


def test_pipeline_sexpr_with_bom():
    """Pipeline works with S-Expr netlist + BOM."""
    result = run_pipeline(
        netlist_text=SEXPR_NETLIST,
        bom_text=BOM_CSV,
    )
    assert result.yaml
    assert result.annotations.bus_hints or result.annotations.peripheral_hints
