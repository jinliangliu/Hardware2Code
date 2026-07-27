"""Tests for generator/context/pin_context.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context.pin_context import process_pins


def test_process_pins_adds_defaults():
    """Pins get default exti, notify_task, af fields"""
    pins = [{"id": "PA5", "function": "GPIO_Output"}]
    result = process_pins(pins)
    assert result[0]["exti"] == {}
    assert result[0]["notify_task"] == ""
    assert result[0]["af"] == 0


def test_process_pins_preserves_existing():
    """Existing pin fields are not overwritten"""
    pins = [{
        "id": "PA0",
        "function": "GPIO_Input",
        "af": 5,
        "notify_task": "btn_task",
        "exti": {"enable": True, "trigger": "rising"}
    }]
    result = process_pins(pins)
    assert result[0]["af"] == 5
    assert result[0]["notify_task"] == "btn_task"
    assert result[0]["exti"] == {"enable": True, "trigger": "rising"}


def test_process_pins_empty_list():
    """Empty pin list returns empty"""
    assert process_pins([]) == []


def test_process_pins_multiple_pins():
    """Multiple pins all get defaults applied"""
    pins = [
        {"id": "PA0", "function": "GPIO_Input"},
        {"id": "PA5", "function": "GPIO_Output", "label": "LED"},
    ]
    result = process_pins(pins)
    for pin in result:
        assert "exti" in pin
        assert "notify_task" in pin
        assert "af" in pin
        assert pin["exti"] == {}
        assert pin["notify_task"] == ""
        assert pin["af"] == 0


def test_process_pins_none_exti_replaced():
    """None exti field is replaced with empty dict"""
    pins = [{"id": "PB1", "function": "GPIO_Input", "exti": None}]
    result = process_pins(pins)
    assert result[0]["exti"] == {}


def test_process_pins_does_not_modify_original():
    """Original list content is modified in-place, but pin count unchanged"""
    pins = [{"id": "PC13", "function": "GPIO_Input"}]
    result = process_pins(pins)
    assert len(result) == 1
    assert result is pins  # in-place modification


if __name__ == "__main__":
    test_process_pins_adds_defaults()
    test_process_pins_preserves_existing()
    test_process_pins_empty_list()
    test_process_pins_multiple_pins()
    test_process_pins_none_exti_replaced()
    test_process_pins_does_not_modify_original()
    print("All pin_context tests passed.")
