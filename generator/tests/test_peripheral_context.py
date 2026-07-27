"""Tests for generator/context/peripheral_context.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context.peripheral_context import detect_peripherals
from context.bearer_context import associate_bearers


# ---------- Mock model data ----------

def _load_model(model_type: str) -> dict:
    """Mock model loader that returns appropriate model dicts by type."""
    models = {
        "Internal_RTC": {
            "model": "STM32G0_RTC",
            "type": "Internal_RTC",
            "interface": "internal",
            "driver_template": "drivers/drv_rtc.c.j2",
            "header_template": "drivers/drv_rtc.h.j2",
        },
        "Internal_PWM": {
            "model": "PWM_Timer",
            "type": "Internal_PWM",
            "interface": "internal",
            "driver_template": "drivers/drv_pwm.c.j2",
            "header_template": "drivers/drv_pwm.h.j2",
        },
        "Internal_ADC": {
            "model": "ADC_Internal",
            "type": "Internal_ADC",
            "interface": "internal",
            "driver_template": "drivers/drv_adc.c.j2",
            "header_template": "drivers/drv_adc.h.j2",
        },
        "Internal_IR": {
            "model": "IR_Internal",
            "type": "Internal_IR",
            "interface": "internal",
            "driver_template": "drivers/drv_ir.c.j2",
            "header_template": "drivers/drv_ir.h.j2",
        },
        "Internal_CLI": {
            "model": "CLI_Internal",
            "type": "Internal_CLI",
            "interface": "internal",
            "driver_template": "drivers/drv_cli.c.j2",
            "header_template": "drivers/drv_cli.h.j2",
        },
        "UART_Serial": {
            "model": "UART_Serial",
            "type": "UART_Serial",
            "interface": "internal",
            "driver_template": "drivers/drv_uart.c.j2",
            "header_template": "drivers/drv_uart.h.j2",
        },
        "I2C_Sensor_MPU6050": {
            "model": "MPU6050",
            "type": "I2C_Sensor",
            "interface": "I2C",
            "driver_template": "drivers/drv_i2c_mpu6050.c.j2",
            "header_template": "drivers/drv_i2c_mpu6050.h.j2",
        },
        "I2C_EEPROM": {
            "model": "I2C_EEPROM",
            "type": "I2C_EEPROM",
            "interface": "I2C",
            "driver_template": "drivers/drv_eeprom.c.j2",
            "header_template": "drivers/drv_eeprom.h.j2",
        },
        "SPI_Flash_W25Q32": {
            "model": "SPI_Flash_W25Q32",
            "type": "SPI_Flash_W25Q32",
            "interface": "SPI",
            "driver_template": "drivers/drv_spi_flash.c.j2",
            "header_template": "drivers/drv_spi_flash.h.j2",
        },
        "SPI_Flash_Generic": {
            "model": "SPI_Flash_Generic",
            "type": "SPI_Flash_Generic",
            "interface": "SPI",
            "driver_template": "drivers/drv_spi_flash.c.j2",
            "header_template": "drivers/drv_spi_flash.h.j2",
        },
        "RS485": {
            "model": "RS485",
            "type": "RS485",
            "interface": "internal",
            "driver_template": "drivers/drv_rs485.c.j2",
            "header_template": "drivers/drv_rs485.h.j2",
        },
        "Cellular_4G": {
            "model": "Cellular_4G",
            "type": "Cellular_4G",
            "interface": "internal",
            "driver_template": "drivers/drv_cellular.c.j2",
            "header_template": "drivers/drv_cellular.h.j2",
        },
        "Protocol_MQTT": {
            "model": "MQTT_Protocol",
            "type": "Protocol_MQTT",
            "interface": "internal",
            "driver_template": "drivers/drv_mqtt.c.j2",
            "header_template": "drivers/drv_mqtt.h.j2",
        },
        "Protocol_Modbus": {
            "model": "Modbus_Protocol",
            "type": "Protocol_Modbus",
            "interface": "internal",
            "driver_template": "drivers/drv_modbus.c.j2",
            "header_template": "drivers/drv_modbus.h.j2",
        },
    }
    return models.get(model_type, {
        "model": "Unknown",
        "type": model_type,
        "interface": "internal",
    })


# ---------- Tests ----------

def test_detect_rtc():
    """RTC peripheral sets has_rtc=True"""
    peripherals = [{"name": "rtc1", "type": "Internal_RTC"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_rtc"] is True
    assert len(result["drivers"]) == 1
    assert result["drivers"][0]["name"] == "rtc1"


def test_detect_i2c():
    """I2C sensor sets has_i2c=True"""
    peripherals = [{"name": "mpu", "type": "I2C_Sensor_MPU6050", "bus": "I2C1"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_i2c"] is True
    assert result["has_mpu6050"] is True


def test_detect_spi():
    """SPI flash sets has_spi=True and has_spi_flash=True"""
    peripherals = [{"name": "flash", "type": "SPI_Flash_Generic", "bus": "SPI1"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_spi"] is True
    assert result["has_spi_flash"] is True


def test_detect_uart():
    """UART serial sets has_uart=True"""
    peripherals = [{"name": "serial1", "type": "UART_Serial"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_uart"] is True
    assert result["uart_name"] == "serial1"


def test_detect_cli():
    """CLI sets has_cli=True and has_uart=True"""
    peripherals = [{"name": "cli0", "type": "Internal_CLI", "uart": "uart2"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_cli"] is True
    assert result["has_uart"] is True
    assert result["cli_uart_name"] == "uart2"


def test_detect_modbus():
    """Modbus protocol sets has_modbus=True via associate_bearers"""
    peripherals = [{"name": "mb1", "type": "Protocol_Modbus", "bearer": "rs485_1"}]
    result = associate_bearers(peripherals, [])
    assert result["has_modbus"] is True
    assert result["modbus_name"] == "mb1"


def test_detect_mqtt():
    """MQTT protocol sets has_mqtt=True via associate_bearers"""
    peripherals = [{"name": "mqtt1", "type": "Protocol_MQTT", "bearer": "cell1"}]
    result = associate_bearers(peripherals, [])
    assert result["has_mqtt"] is True


def test_detect_pwm():
    """PWM peripheral sets has_pwm=True"""
    peripherals = [{"name": "pwm1", "type": "Internal_PWM"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_pwm"] is True


def test_detect_adc():
    """ADC peripheral sets has_adc=True"""
    peripherals = [{"name": "adc1", "type": "Internal_ADC"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_adc"] is True


def test_detect_rs485():
    """RS485 sets has_rs485=True and has_uart=True"""
    peripherals = [{"name": "rs485_1", "type": "RS485"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_rs485"] is True
    assert result["has_uart"] is True


def test_detect_cellular():
    """Cellular_4G sets has_cellular=True and has_uart=True"""
    peripherals = [{"name": "cell1", "type": "Cellular_4G"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_cellular"] is True
    assert result["has_uart"] is True


def test_detect_ir():
    """IR peripheral sets has_ir=True"""
    peripherals = [{"name": "ir1", "type": "Internal_IR"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_ir"] is True


def test_detect_multiple():
    """Multiple peripherals detected correctly"""
    peripherals = [
        {"name": "rtc1", "type": "Internal_RTC"},
        {"name": "serial1", "type": "UART_Serial"},
        {"name": "mqtt1", "type": "Protocol_MQTT", "bearer": "cell1"},
    ]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_rtc"] is True
    assert result["has_uart"] is True
    assert len(result["drivers"]) == 3
    bearer_result = associate_bearers(peripherals, result["drivers"])
    assert bearer_result["has_mqtt"] is True


def test_empty_peripherals():
    """No peripherals, all flags False"""
    result = detect_peripherals([], _load_model)
    assert result["has_rtc"] is False
    assert result["has_i2c"] is False
    assert result["has_spi"] is False
    assert result["has_uart"] is False
    assert result["has_cli"] is False
    assert result["has_pwm"] is False
    assert result["has_adc"] is False
    assert result["has_rs485"] is False
    assert result["has_cellular"] is False
    assert result["has_ir"] is False
    assert result["drivers"] == []
    bearer_result = associate_bearers([], [])
    assert bearer_result["has_mqtt"] is False
    assert bearer_result["has_modbus"] is False


def test_detect_rs485_with_uart_ref():
    """RS485 with uart ref sets uart_name"""
    peripherals = [{"name": "rs485_1", "type": "RS485", "uart": "usart1"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_rs485"] is True
    assert result["has_uart"] is True
    assert result["uart_name"] == "usart1"


def test_detect_cellular_with_uart_extra():
    """Cellular_4G with uart in extra sets uart_name"""
    peripherals = [{"name": "cell1", "type": "Cellular_4G",
                     "extra": {"uart": "usart3"}}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_cellular"] is True
    assert result["has_uart"] is True
    assert result["uart_name"] == "usart3"


def test_detect_spi_flash_w25q32():
    """SPI_Flash_W25Q32 sets has_spi_flash=True"""
    peripherals = [{"name": "flash", "type": "SPI_Flash_W25Q32", "bus": "SPI1"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_spi"] is True
    assert result["has_spi_flash"] is True


def test_detect_cli_without_uart_ref():
    """CLI without uart ref still sets has_cli"""
    peripherals = [{"name": "cli0", "type": "Internal_CLI"}]
    result = detect_peripherals(peripherals, _load_model)
    assert result["has_cli"] is True
    assert result["has_uart"] is True


if __name__ == "__main__":
    test_detect_rtc()
    test_detect_i2c()
    test_detect_spi()
    test_detect_uart()
    test_detect_cli()
    test_detect_modbus()
    test_detect_mqtt()
    test_detect_pwm()
    test_detect_adc()
    test_detect_rs485()
    test_detect_cellular()
    test_detect_ir()
    test_detect_multiple()
    test_empty_peripherals()
    print("All peripheral_context tests passed.")
