#!/usr/bin/env python3
"""
Hardware2Code Generator
读取硬件 YAML，生成 STM32G0 + FreeRTOS 工程，包含单元测试。
"""

import argparse
import os
import sys
import shutil

import yaml
from jinja2 import Environment, FileSystemLoader

# 导入本地模块
from context_builder import build_context
from validator import validate_hardware


def load_yaml(file_path: str) -> dict:
    """加载硬件描述 YAML 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_templates(env: Environment, context: dict, output_dir: str):
    """渲染所有模板并写入输出目录，包括测试框架"""
    # 创建必要的子目录
    os.makedirs(os.path.join(output_dir, "src", "drivers"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "config"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "linker"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "test", "unity"), exist_ok=True)

    # ---------- 标准模板列表 ----------
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

    # ---------- 事件管理器模板 ----------
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

    # ---------- 外设驱动模板 ----------
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

    # ---------- 测试框架 ----------
    test_dir = os.path.join(output_dir, "test")
    os.makedirs(test_dir, exist_ok=True)

    # 复制 Unity 源文件到 test/unity/
    unity_src = os.path.join("static", "unity")
    if os.path.exists(unity_src):
        shutil.copytree(unity_src, os.path.join(test_dir, "unity"), dirs_exist_ok=True)
        print("Copied Unity framework to test/unity/")
    else:
        print("Warning: static/unity not found. Tests will not compile without Unity.")

    # Mock HAL 模板
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

    # 如果存在 RTC，添加 RTC 测试
    if context.get("has_rtc"):
        test_templates["test/test_rtc.c.j2"] = os.path.join(test_dir, "test_rtc.c")
        test_templates["test/test_event_mgr.c.j2"] = os.path.join(test_dir, "test_event_mgr.c")

    # 如果存在 MPU6050，添加其测试
    for p in context.get("peripherals", []):
        if p.get("type") == "I2C_Sensor_MPU6050":
            test_templates["test/test_mpu6050.c.j2"] = os.path.join(test_dir, "test_mpu6050.c")
            break  # 只加一次

    for tmpl_name, out_path in test_templates.items():
        template = env.get_template(tmpl_name)
        rendered = template.render(context)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out_path}")

    # 复制 run_tests.py 脚本到 test/
    run_tests_script = os.path.join("generator", "run_tests.py")
    if os.path.exists(run_tests_script):
        shutil.copy(run_tests_script, os.path.join(test_dir, "run_tests.py"))
        print("Copied run_tests.py to test/")
    else:
        print("Warning: run_tests.py not found in generator/. Tests will not be executable via make test.")


def generate(hardware_yaml: str, output_dir: str):
    # 加载硬件描述
    try:
        hw = load_yaml(hardware_yaml)
    except Exception as e:
        print(f"Error loading YAML file: {e}")
        sys.exit(1)

    # 校验硬件描述
    errors = validate_hardware(hw)
    if errors:
        print("Errors in hardware YAML:")
        for err in errors:
            print(f"  - {err}")
        print("Please fix the errors and try again.")
        sys.exit(1)

    project_name = os.path.basename(output_dir) or "hw2code"

    # 构建上下文
    context = build_context(hw, project_name)

    # 初始化 Jinja2 环境，模板目录为 templates/
    env = Environment(
        loader=FileSystemLoader("templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # 渲染所有模板
    try:
        render_templates(env, context, output_dir)
    except Exception as e:
        print(f"Error during template rendering: {e}")
        sys.exit(1)

    print(f"\nProject '{project_name}' generated successfully in '{output_dir}'")


def main():
    parser = argparse.ArgumentParser(description="Hardware2Code Generator")
    parser.add_argument("-i", "--input", required=True, help="Path to hardware YAML file")
    parser.add_argument("-o", "--output", required=True, help="Output directory for generated project")
    args = parser.parse_args()

    generate(args.input, args.output)


if __name__ == "__main__":
    main()