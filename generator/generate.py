#!/usr/bin/env python3
"""
Hardware2Code Generator
读取硬件 YAML，生成 STM32G0 + FreeRTOS 工程（或 HIL 测试固件）。
"""

import argparse
import os
import sys
import shutil

import yaml
from jinja2 import Environment, FileSystemLoader

from context_builder import build_context
from validator import validate_hardware


def load_yaml(file_path: str) -> dict:
    """加载硬件描述 YAML 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_hil_project(env: Environment, context: dict, output_dir: str):
    """渲染 HIL 测试固件工程"""
    os.makedirs(os.path.join(output_dir, "src", "drivers"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "config"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "linker"), exist_ok=True)

    # 复制 Unity 源文件
    unity_src = os.path.join("static", "unity")
    if os.path.exists(unity_src):
        shutil.copytree(unity_src, os.path.join(output_dir, "unity"), dirs_exist_ok=True)
        print("Copied Unity to unity/")
    else:
        print("Warning: static/unity not found. HIL tests will not compile.")

    # 生成 HIL 主固件
    hil_main = env.get_template("test/hil_test.c.j2")
    rendered = hil_main.render(context)
    with open(os.path.join(output_dir, "src", "main.c"), "w", encoding="utf-8") as f:
        f.write(rendered)
    print("Generated HIL main.c")

    # 生成必要的标准文件
    standard = {
        "config/stm32g0xx_hal_conf.h.j2": os.path.join(output_dir, "config", "stm32g0xx_hal_conf.h"),
        "linker/STM32G0B1RETx_FLASH.ld.j2": os.path.join(output_dir, "linker", "STM32G0B1RETx_FLASH.ld"),
        "project/Makefile.j2": os.path.join(output_dir, "Makefile"),
    }
    for tmpl, out in standard.items():
        template = env.get_template(tmpl)
        rendered = template.render(context)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out}")

    # 复制 hil_runner.py
    hil_runner_src = os.path.join("generator", "hil_runner.py")
    if os.path.exists(hil_runner_src):
        shutil.copy(hil_runner_src, os.path.join(output_dir, "hil_runner.py"))
        print("Copied hil_runner.py")
    else:
        print("Warning: generator/hil_runner.py not found")

    print(f"\nHIL project '{os.path.basename(output_dir)}' generated successfully.")


def render_templates(env: Environment, context: dict, output_dir: str):
    """渲染所有模板并写入输出目录，包括测试框架"""
    os.makedirs(os.path.join(output_dir, "src", "drivers"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "config"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "linker"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "test", "unity"), exist_ok=True)

    # ---------- 标准模板 ----------
    standard_templates = {
        "src/main.c.j2": os.path.join(output_dir, "src", "main.c"),
        "src/gpio.c.j2": os.path.join(output_dir, "src", "gpio.c"),
        "src/sleep.c.j2": os.path.join(output_dir, "src", "sleep.c"),
        "src/stm32g0xx_it.c.j2": os.path.join(output_dir, "src", "stm32g0xx_it.c"),
        "config/FreeRTOSConfig.h.j2": os.path.join(output_dir, "config", "FreeRTOSConfig.h"),
        "config/stm32g0xx_hal_conf.h.j2": os.path.join(output_dir, "config", "stm32g0xx_hal_conf.h"),
        "linker/STM32G0B1RETx_FLASH.ld.j2": os.path.join(output_dir, "linker", "STM32G0B1RETx_FLASH.ld"),
        "project/Makefile.j2": os.path.join(output_dir, "Makefile"),
    }

    for template_name, out_path in standard_templates.items():
        template = env.get_template(template_name)
        rendered = template.render(context)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out_path}")

    # ---------- 事件管理器 ----------
    event_mgr_templates = {
        "src/event_mgr.h.j2": os.path.join(output_dir, "src", "event_mgr.h"),
        "src/event_mgr.c.j2": os.path.join(output_dir, "src", "event_mgr.c"),
    }
    for tmpl_name, out_path in event_mgr_templates.items():
        template = env.get_template(tmpl_name)
        rendered = template.render(context)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out_path}")

    # ---------- 外设驱动 ----------
    drivers = context.get("drivers", [])
    for drv in drivers:
        if drv.get("header_template"):
            template = env.get_template(drv["header_template"])
            rendered = template.render(peripheral=drv["peripheral"], model=drv["model"])
            out_path = os.path.join(output_dir, "src", "drivers", f"drv_{drv['name']}.h")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rendered)
            print(f"Generated: {out_path}")

        if drv.get("template"):
            template = env.get_template(drv["template"])
            rendered = template.render(peripheral=drv["peripheral"], model=drv["model"])
            out_path = os.path.join(output_dir, "src", "drivers", f"drv_{drv['name']}.c")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rendered)
            print(f"Generated: {out_path}")

    # ---------- 业务状态机 ----------
    if context.get("has_business_flow"):
        state_machine_templates = {
            "app/statemachine.h.j2": os.path.join(output_dir, "src", "statemachine.h"),
            "app/statemachine.c.j2": os.path.join(output_dir, "src", "statemachine.c"),
        }
        for tmpl_name, out_path in state_machine_templates.items():
            template = env.get_template(tmpl_name)
            rendered = template.render(context)
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(rendered)
            print(f"Generated: {out_path}")

    # ---------- 测试框架 ----------
    test_dir = os.path.join(output_dir, "test")
    os.makedirs(test_dir, exist_ok=True)

    # 复制 Unity
    unity_src = os.path.join("static", "unity")
    if os.path.exists(unity_src):
        shutil.copytree(unity_src, os.path.join(test_dir, "unity"), dirs_exist_ok=True)
        print("Copied Unity framework to test/unity/")
    else:
        print("Warning: static/unity not found. Tests will not compile without Unity.")

    # Mock HAL
    mock_templates = {
        "test/mock_hal.h.j2": os.path.join(test_dir, "mock_hal.h"),
        "test/mock_hal.c.j2": os.path.join(test_dir, "mock_hal.c"),
    }
    for tmpl_name, out_path in mock_templates.items():
        template = env.get_template(tmpl_name)
        rendered = template.render(context)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out_path}")

    # 测试用例模板（根据外设动态生成）
    test_templates = {
        "test/test_gpio.c.j2": os.path.join(test_dir, "test_gpio.c"),
    }

    if context.get("has_rtc"):
        test_templates["test/test_rtc.c.j2"] = os.path.join(test_dir, "test_rtc.c")
        test_templates["test/test_event_mgr.c.j2"] = os.path.join(test_dir, "test_event_mgr.c")
        test_templates["test/test_rtc_timers.c.j2"] = os.path.join(test_dir, "test_rtc_timers.c")

    for p in context.get("peripherals", []):
        if p.get("type") == "I2C_Sensor_MPU6050":
            test_templates["test/test_mpu6050.c.j2"] = os.path.join(test_dir, "test_mpu6050.c")
            break

    if context.get("has_spi_flash"):
        test_templates["test/test_spi_flash.c.j2"] = os.path.join(test_dir, "test_spi_flash.c")

    if context.get("has_pwm"):
        test_templates["test/test_pwm.c.j2"] = os.path.join(test_dir, "test_pwm.c")

    if context.get("has_adc"):
        test_templates["test/test_adc.c.j2"] = os.path.join(test_dir, "test_adc.c")

    if context.get("has_uart"):
        test_templates["test/test_uart.c.j2"] = os.path.join(test_dir, "test_uart.c")

    # 状态机测试
    if context.get("has_business_flow"):
        # 暂时只为 rtc_advanced 生成状态机测试，substate_demo 跳过
        if context.get("project_name") == "rtc_adv":
            if context.get("business_flow", {}).get("regions") is not None:
                test_templates["test/test_parallel.c.j2"] = os.path.join(test_dir, "test_parallel.c")
            else:
                test_templates["test/test_statemachine.c.j2"] = os.path.join(test_dir, "test_statemachine.c")

    for tmpl_name, out_path in test_templates.items():
        template = env.get_template(tmpl_name)
        rendered = template.render(context)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out_path}")

    # 复制 run_tests.py
    run_tests_script = os.path.join("generator", "run_tests.py")
    if os.path.exists(run_tests_script):
        shutil.copy(run_tests_script, os.path.join(test_dir, "run_tests.py"))
        print("Copied run_tests.py to test/")
    else:
        print("Warning: run_tests.py not found in generator/. Tests will not be executable via make test.")


def generate(hardware_yaml: str, output_dir: str, hil_mode: bool = False):
    try:
        hw = load_yaml(hardware_yaml)
    except Exception as e:
        print(f"Error loading YAML file: {e}")
        sys.exit(1)

    errors = validate_hardware(hw)
    if errors:
        print("Errors in hardware YAML:")
        for err in errors:
            print(f"  - {err}")
        print("Please fix the errors and try again.")
        sys.exit(1)

    project_name = os.path.basename(output_dir) or "hw2code"
    context = build_context(hw, project_name, hil_mode)

    env = Environment(
        loader=FileSystemLoader("templates", encoding='utf-8'),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    try:
        if hil_mode:
            render_hil_project(env, context, output_dir)
        else:
            render_templates(env, context, output_dir)
    except Exception as e:
        print(f"Error during template rendering: {e}")
        sys.exit(1)

    print(f"\nProject '{project_name}' generated successfully in '{output_dir}'")


def main():
    parser = argparse.ArgumentParser(description="Hardware2Code Generator")
    parser.add_argument("-i", "--input", required=True, help="Path to hardware YAML file")
    parser.add_argument("-o", "--output", required=True, help="Output directory for generated project")
    parser.add_argument("--hil", action="store_true", help="Generate HIL test firmware")
    args = parser.parse_args()

    generate(args.input, args.output, args.hil)


if __name__ == "__main__":
    main()