"""Tests for CSV BOM parser."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from parser.bom_parser import parse_bom_string


SAMPLE_BOM = """Id,Designator,Value,Footprint,Quantity,LCSC Part#
1,U1,STM32G0B1RET6,LQFP-64_10x10mm_P0.5mm,1,C12345
2,U2,MPU6050,QFN-24_4x4mm_P0.5mm,1,C67890
3,U3,W25Q32JVSSIQ,SOIC-8_5.23x5.23mm_P1.27mm,1,C11111
4,"R1,R2",10k,R_0805,2,C22222
5,"D1,D2",LED_RED,LED_0805,2,C33333
"""


def test_parse_mcu():
    """MCU should be detected from BOM."""
    result = parse_bom_string(SAMPLE_BOM)
    import yaml
    hw = yaml.safe_load(result)
    assert hw["mcu"]["part"] == "STM32G0B1RET6", "Wrong MCU part"


def test_parse_i2c_peripheral():
    """I2C peripheral (MPU6050) should be mapped."""
    result = parse_bom_string(SAMPLE_BOM)
    assert "MPU6050" in result, "MPU6050 not found"
    assert "I2C_Sensor_MPU6050" in result, "Wrong peripheral type"


def test_parse_spi_peripheral():
    """SPI Flash (W25Q32) should be mapped."""
    result = parse_bom_string(SAMPLE_BOM)
    assert "SPI_Flash_W25Q32" in result, "SPI Flash not found"


def test_parse_led_gpio():
    """LED components should generate GPIO_Output pins."""
    result = parse_bom_string(SAMPLE_BOM)
    import yaml
    hw = yaml.safe_load(result)
    pins = hw.get("pins", [])
    led_pins = [p for p in pins if "LED" in p.get("label", "")]
    assert len(led_pins) > 0, "No LED pins found"


def test_parse_app_tasks():
    """App tasks should be generated for peripherals."""
    result = parse_bom_string(SAMPLE_BOM)
    assert "mpu6050_task" in result, "mpu6050 task not found"
    assert "w25q32jvssiq_task" in result, "w25q32 task not found"


def test_empty_bom():
    """Empty BOM should still produce valid YAML with default MCU."""
    empty_csv = "Id,Designator,Value,Footprint,Quantity\n"
    result = parse_bom_string(empty_csv)
    import yaml
    hw = yaml.safe_load(result)
    assert "mcu" in hw, "mcu section missing"


# ---------- More peripheral tests ----------

EXTRA_BOM = """Id,Designator,Value,Footprint,Quantity,LCSC Part#
1,U1,STM32G0B1RET6,LQFP-64,1,C12345
2,U4,AT24C256,SOIC-8,1,C99999
3,U5,MAX485,SOIC-8,1,C88888
4,U6,SIM800,LGA-68,1,C77777
5,SW1,BUTTON,THT-4pin,1,C66666
6,D3,LED_BLUE,LED_0805,1,C55555
"""


def test_parse_eeprom_peripheral():
    """EEPROM (AT24C256) should be mapped to I2C_EEPROM."""
    result = parse_bom_string(EXTRA_BOM)
    assert "I2C_EEPROM" in result, "I2C_EEPROM not found"


def test_parse_rs485_peripheral():
    """RS485 transceiver (MAX485) should be mapped."""
    result = parse_bom_string(EXTRA_BOM)
    assert "RS485" in result, "RS485 not found"


def test_parse_cellular_peripheral():
    """Cellular module (SIM800) should be mapped."""
    result = parse_bom_string(EXTRA_BOM)
    assert "Cellular_4G" in result, "Cellular_4G not found"


def test_parse_button_in_bom():
    """Button component should generate GPIO_Input with EXTI."""
    result = parse_bom_string(EXTRA_BOM)
    import yaml
    hw = yaml.safe_load(result)
    btn_pins = [p for p in hw.get("pins", []) if "BUTTON" in p.get("label", "")]
    assert len(btn_pins) > 0, "No button pins found"
    assert btn_pins[0].get("exti", {}).get("enable") == True


# ---------- File-based parse ----------

def test_parse_bom_from_file():
    """parse_bom from a file path works."""
    import tempfile
    from parser.bom_parser import parse_bom

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                       delete=False, encoding='utf-8') as f:
        f.write(SAMPLE_BOM)
        tmp_path = f.name

    try:
        result = parse_bom(tmp_path)
        import yaml
        hw = yaml.safe_load(result)
        assert hw["mcu"]["part"] == "STM32G0B1RET6"
    finally:
        os.unlink(tmp_path)


def test_parse_bom_file_not_found():
    """parse_bom with missing file raises FileNotFoundError."""
    from parser.bom_parser import parse_bom
    try:
        parse_bom("nonexistent_xyz_file.csv")
        assert False, "Should have raised"
    except FileNotFoundError:
        pass
