"""Tests for generator/context/bearer_context.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context.bearer_context import associate_bearers


def test_associate_bearers_mqtt():
    """MQTT protocol detected"""
    peripherals = [{"name": "mqtt1", "type": "Protocol_MQTT"}]
    result = associate_bearers(peripherals, [])
    assert result["has_mqtt"] == True
    assert result["has_modbus"] == False


def test_associate_bearers_modbus():
    """Modbus protocol detected"""
    peripherals = [{"name": "modbus1", "type": "Protocol_Modbus"}]
    result = associate_bearers(peripherals, [])
    assert result["has_modbus"] == True
    assert result["modbus_name"] == "modbus1"


def test_associate_bearers_both():
    """Both MQTT and Modbus detected"""
    peripherals = [
        {"name": "mqtt1", "type": "Protocol_MQTT"},
        {"name": "modbus1", "type": "Protocol_Modbus"},
    ]
    result = associate_bearers(peripherals, [])
    assert result["has_mqtt"] == True
    assert result["has_modbus"] == True


def test_associate_bearers_none():
    """No protocol peripherals"""
    peripherals = [{"name": "rtc1", "type": "Internal_RTC"}]
    result = associate_bearers(peripherals, [])
    assert result["has_mqtt"] == False
    assert result["has_modbus"] == False


if __name__ == "__main__":
    test_associate_bearers_mqtt()
    test_associate_bearers_modbus()
    test_associate_bearers_both()
    test_associate_bearers_none()
    print("All bearer_context tests passed.")
