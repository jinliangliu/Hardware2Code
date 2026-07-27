"""Tests for generator/context/builder.py"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from context.builder import load_model, build_context


def test_load_model_internal_rtc():
    """load_model should return a dict for Internal_RTC"""
    model = load_model("Internal_RTC")
    assert isinstance(model, dict)
    assert model.get("type") == "Internal_RTC"


def test_load_model_internal_cli():
    """load_model should return a dict for Internal_CLI"""
    model = load_model("Internal_CLI")
    assert isinstance(model, dict)
    assert model.get("type") == "Internal_CLI"


def test_load_model_uart_serial():
    """load_model should return a dict for UART_Serial"""
    model = load_model("UART_Serial")
    assert isinstance(model, dict)
    assert model.get("type") == "UART_Serial"


def test_load_model_nonexistent():
    """load_model should return empty dict for nonexistent type"""
    model = load_model("NonExistent_XYZ_123")
    assert model == {}


def test_load_model_i2c_sensor():
    """load_model should return dict for I2C_Sensor_MPU6050"""
    model = load_model("I2C_Sensor_MPU6050")
    assert isinstance(model, dict)
    assert model.get("type") == "I2C_Sensor"


def test_build_context_minimal():
    """build_context with minimal config returns valid context"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
    }
    ctx = build_context(hw, "test_project")
    assert ctx["project_name"] == "test_project"
    assert ctx["mcu"]["part"] == "STM32G0B1RET6"
    assert ctx["mcu"]["core_clock_mhz"] == 64
    assert ctx["has_i2c"] == False
    assert ctx["has_rtc"] == False
    assert ctx["has_bootloader"] == False
    assert ctx["has_business_flow"] == False
    assert ctx["hil_mode"] == False
    assert isinstance(ctx["hal_sources"], list)
    assert "stm32g0xx_hal.c" in ctx["hal_sources"]


def test_build_context_with_rtc():
    """build_context with RTC peripheral sets has_rtc and rtc_prediv"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "peripherals": [{"name": "rtc1", "type": "Internal_RTC"}],
    }
    ctx = build_context(hw, "test_rtc")
    assert ctx["has_rtc"] == True
    assert ctx["rtc_async_prediv"] == 127
    assert ctx["rtc_sync_prediv"] == 255
    assert "stm32g0xx_hal_rtc.c" in ctx["hal_sources"]


def test_build_context_with_bootloader():
    """build_context with bootloader sets has_bootloader"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "bootloader": {"enabled": True},
    }
    ctx = build_context(hw, "test_boot")
    assert ctx["has_bootloader"] == True
    assert "stm32g0xx_hal_iwdg.c" in ctx["hal_sources"]


def test_build_context_with_business_flow():
    """build_context with business_flow sets has_business_flow"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "business_flow": {
            "states": [
                {"name": "idle",
                 "transitions": [{"event": "TICK", "target": "idle"}]},
            ]
        },
    }
    ctx = build_context(hw, "test_bf")
    assert ctx["has_business_flow"] == True
    assert ctx["has_event_mgr"] == True


def test_build_context_default_hil():
    """build_context creates default HIL config when none provided"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
    }
    ctx = build_context(hw, "test_hil")
    assert ctx["hil"]["baudrate"] == 115200
    assert ctx["hil"]["uart"] == "UART2"


def test_build_context_with_led():
    """build_context detects LED label on pin"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [
            {"id": "PA5", "function": "GPIO_Output", "label": "LED"},
        ],
        "app_tasks": [{"name": "led_task", "priority": 5}],
    }
    ctx = build_context(hw, "test_led")
    assert ctx["has_led"] == True
    assert ctx["has_led_task"] == True


def test_build_context_heap_stack():
    """build_context uses custom heap/stack sizes"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "heap_size": "0x800",
        "stack_size": "0x1000",
    }
    ctx = build_context(hw, "test_mem")
    assert ctx["heap_size"] == "0x800"
    assert ctx["stack_size"] == "0x1000"


def test_build_context_hil_mode():
    """build_context in hil_mode adds UART HAL"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
    }
    ctx = build_context(hw, "test_hil", hil_mode=True)
    assert ctx["hil_mode"] == True
    assert "stm32g0xx_hal_uart.c" in ctx["hal_sources"]


def test_build_context_with_defer_timeline():
    """build_context processes defer and timeline actions"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "business_flow": {
            "states": [
                {"name": "idle",
                 "on_entry": ["defer 3000 => toggle_led"],
                 "transitions": [
                     {"event": "TICK", "target": "active",
                      "actions": ["timeline: 1000=>toggle_led"]}
                 ]},
                {"name": "active"},
            ]
        },
    }
    ctx = build_context(hw, "test_defer")
    assert ctx["has_business_flow"] == True
    assert len(ctx["defer_actions"]) >= 2
    assert len(ctx["defer_timer_names"]) >= 2


def test_build_context_with_publish():
    """build_context collects published events"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "business_flow": {
            "states": [
                {"name": "idle",
                 "transitions": [
                     {"event": "TICK", "target": "active",
                      "actions": ["publish ALARM"]}
                 ]},
                {"name": "active"},
            ]
        },
    }
    ctx = build_context(hw, "test_pub")
    assert ctx["has_business_flow"] == True
    assert "ALARM" in ctx["published_events"]


def test_build_context_with_dict_actions():
    """build_context normalizes dict-format actions"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "business_flow": {
            "states": [
                {"name": "idle",
                 "on_entry": [
                     {"defer": {"after": 500, "do": "toggle_led"}},
                     {"timeline": [{"ms": 200, "do": "toggle_led"}]},
                     {"set": {"var": "counter", "value": 10}},
                     {"start_timer": {"name": "t1", "ms": 1000}},
                     {"stop_timer": {"name": "t1"}},
                 ],
                 "transitions": [
                     {"event": "TICK", "target": "idle"}
                 ]},
            ]
        },
    }
    ctx = build_context(hw, "test_dict")
    assert ctx["has_business_flow"] == True


def test_build_context_compound_state():
    """build_context handles compound states (states within states)"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "business_flow": {
            "states": [
                {"name": "parent", "initial_state": "child1",
                 "states": [
                     {"name": "child1",
                      "transitions": [{"event": "GO", "target": "child2"}]},
                     {"name": "child2"},
                 ]},
            ]
        },
    }
    ctx = build_context(hw, "test_cmpd")
    assert ctx["has_business_flow"] == True
    assert ctx["has_substate"] == True


def test_build_context_with_fota():
    """build_context with bootloader + UART sets has_fota"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "bootloader": {"enabled": True},
        "peripherals": [{"name": "uart1", "type": "UART_Serial"}],
    }
    ctx = build_context(hw, "test_fota")
    assert ctx["has_bootloader"] == True
    assert ctx["has_uart"] == True
    assert ctx["has_fota"] == True


def test_build_context_with_regions():
    """build_context handles business_flow with regions"""
    hw = {
        "mcu": {"part": "STM32G0B1RET6"},
        "pins": [{"id": "PA5", "function": "GPIO_Output"}],
        "business_flow": {
            "regions": [
                {"name": "r1", "initial_state": "s1",
                 "states": [
                     {"name": "s1",
                      "transitions": [{"event": "E1", "target": "s2"}]},
                     {"name": "s2"},
                 ]},
            ]
        },
    }
    ctx = build_context(hw, "test_regions")
    assert ctx["has_business_flow"] == True


if __name__ == "__main__":
    test_load_model_internal_rtc()
    test_load_model_internal_cli()
    test_load_model_uart_serial()
    test_load_model_nonexistent()
    test_load_model_i2c_sensor()
    test_build_context_minimal()
    test_build_context_with_rtc()
    test_build_context_with_bootloader()
    test_build_context_with_business_flow()
    test_build_context_default_hil()
    test_build_context_with_led()
    test_build_context_heap_stack()
    test_build_context_hil_mode()
    print("All builder tests passed.")
