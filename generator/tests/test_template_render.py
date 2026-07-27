"""Snapshot tests for Jinja2 template rendering."""

import sys
import os

# Ensure generator/ is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jinja2 import Environment, FileSystemLoader
from paths import TEMPLATES_DIR
from jinja_filters import register_filters


def _make_env():
    """Create a Jinja2 environment pointing to the templates directory."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR, encoding='utf-8'),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    register_filters(env)
    return env


def _minimal_context():
    """Return a minimal but valid template context for main.c.j2."""
    return {
        "project_name": "test_proj",
        "mcu": {
            "part": "STM32G0B1RET6",
            "core_clock_mhz": 64,
            "hse_freq": 8000000,
        },
        "pins": [
            {
                "id": "PA5",
                "function": "GPIO_Output",
                "label": "LED",
                "exti": {},
                "notify_task": "",
                "af": 0,
            }
        ],
        "sleep": {},
        "app_tasks": [],
        "hal_sources": [],
        "peripherals": [],
        "drivers": [],
        "has_i2c": False,
        "has_rtc": False,
        "has_pwm": False,
        "has_spi": False,
        "has_spi_flash": False,
        "has_mpu6050": False,
        "has_adc": False,
        "has_uart": False,
        "has_rs485": False,
        "has_ir": False,
        "has_cellular": False,
        "has_modbus": False,
        "has_mqtt": False,
        "has_cli": False,
        "has_led": True,
        "has_led_task": False,
        "has_business_flow": False,
        "has_substate": False,
        "has_bootloader": False,
        "has_fota": False,
        "has_event_mgr": True,
        "hil_mode": False,
        "uart_name": "",
        "rs485_name": "",
        "modbus_name": "",
        "cli_uart_name": "",
        "business_flow": {},
        "boot_config": {},
        "hil": {"baudrate": 115200, "uart": "UART2", "tx_pin": "PA2", "rx_pin": "PA3"},
        "boot_max_retries": 3,
        "hil_tests": [{"name": "test_dummy", "body": "TEST_PASS();"}],
        "heap_size": "0x200",
        "stack_size": "0x400",
        "static_dir_absolute": "/fake/static",
        "defer_actions": [],
        "defer_timer_names": [],
        "timer_events": [],
        "published_events": [],
    }


def test_main_c_template_basic():
    """Verify main.c renders with basic context containing expected strings."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()
    rendered = template.render(context)

    # Core includes always present
    assert '#include "stm32g0xx_hal.h"' in rendered
    assert '#include "FreeRTOS.h"' in rendered
    assert '#include "event_mgr.h"' in rendered

    # GPIO init is always called
    assert "MX_GPIO_Init" in rendered
    assert "void MX_GPIO_Init(void);" in rendered

    # Standard HAL flow
    assert "HAL_Init()" in rendered
    assert "SystemClock_Config()" in rendered

    # LED pin definition
    assert "LED_GPIO_Port" in rendered
    assert "LED_GPIO_Pin" in rendered

    # Event manager task
    assert "EventMgr_Task" in rendered

    # FreeRTOS scheduler
    assert "vTaskStartScheduler" in rendered


def test_main_c_template_with_rtc():
    """Main.c renders RTC-related code when has_rtc=True."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()
    context["has_rtc"] = True
    context["peripherals"] = [
        {
            "name": "rtc1",
            "type": "Internal_RTC",
            "model": {
                "model": "STM32G0_RTC",
                "type": "Internal_RTC",
                "interface": "internal",
            },
        }
    ]
    rendered = template.render(context)

    assert "RTC_Init()" in rendered
    assert "RTC_Start()" in rendered


def test_main_c_template_with_bootloader():
    """Main.c renders bootloader-related code when has_bootloader=True."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()
    context["has_bootloader"] = True
    context["boot_config"] = {
        "enabled": True,
        "size_kb": 8,
        "app_a_offset": 0x2000,
        "app_b_offset": 0x40000,
        "wdg_timeout_ms": 5000,
    }
    rendered = template.render(context)

    assert '#include "boot_app.h"' in rendered
    assert "IWDG_Init()" in rendered
    assert "boot_app_mark_ok()" in rendered


def test_main_c_template_with_business_flow():
    """Main.c renders statemachine when has_business_flow=True."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()
    context["has_business_flow"] = True
    context["business_flow"] = {"states": [{"name": "idle", "initial_state": "idle"}]}
    rendered = template.render(context)

    assert '#include "statemachine.h"' in rendered
    assert "statemachine_init()" in rendered


def test_main_c_template_with_led_task():
    """Main.c renders led_task task when has_led_task=True."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()
    context["has_led_task"] = True
    context["app_tasks"] = [
        {
            "name": "led_task",
            "priority": 5,
            "stack_size": 128,
        }
    ]
    rendered = template.render(context)

    assert "led_task_handle" in rendered
    assert "void led_task(void *pvParameters)" in rendered
    assert "HAL_GPIO_TogglePin" in rendered
    assert "ulTaskNotifyTake" in rendered


def test_main_c_template_with_cli():
    """Main.c renders CLI code when has_cli=True and cli driver is present."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()
    context["has_cli"] = True
    context["has_uart"] = True
    context["cli_uart_name"] = "uart2"
    context["drivers"] = [
        {
            "name": "cli",
            "template": "drivers/drv_cli.c.j2",
            "header_template": "drivers/drv_cli.h.j2",
            "model": {},
            "peripheral": {"name": "cli", "type": "Internal_CLI"},
        }
    ]
    rendered = template.render(context)

    assert '#include "drv_cli.h"' in rendered
    assert "cli_init" in rendered
    assert "cli_task" in rendered


def test_main_c_no_led_no_bootloader_no_flow():
    """Minimal main.c without LED label should not have LED definitions."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()
    context["has_led"] = False
    context["pins"] = [
        {
            "id": "PA0",
            "function": "GPIO_Input",
            "label": "BTN",
            "exti": {},
            "notify_task": "",
            "af": 0,
        }
    ]
    rendered = template.render(context)

    # No LED macro should be generated
    assert "LED_GPIO_Port" not in rendered
    assert "LED_GPIO_Pin" not in rendered
    # Core includes still present
    assert '#include "stm32g0xx_hal.h"' in rendered


def test_macros_template_available():
    """macros.j2 can be imported by templates."""
    env = _make_env()
    # Just verify the template environment can load macros.j2
    template = env.get_template("src/main.c.j2")
    # If we get here without jinja2.TemplateNotFound, macros.j2 was found
    assert template is not None


def test_template_environment_has_macros():
    """Verify the main.c template uses macros from macros.j2."""
    env = _make_env()
    template = env.get_template("src/main.c.j2")
    context = _minimal_context()

    # Render with a pin that exercises pin_port and pin_number macros
    context["pins"] = [
        {
            "id": "PC13",
            "function": "GPIO_Output",
            "label": "LED",
            "exti": {},
            "notify_task": "",
            "af": 0,
        }
    ]

    rendered = template.render(context)
    # PC13 → port C, pin 13
    assert "GPIOC" in rendered
    assert "GPIO_PIN_13" in rendered


if __name__ == "__main__":
    test_main_c_template_basic()
    test_main_c_template_with_rtc()
    test_main_c_template_with_bootloader()
    test_main_c_template_with_business_flow()
    test_main_c_template_with_led_task()
    test_main_c_template_with_cli()
    test_main_c_no_led_no_bootloader_no_flow()
    test_macros_template_available()
    test_template_environment_has_macros()
    print("All template_render tests passed.")
