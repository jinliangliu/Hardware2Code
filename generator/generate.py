#!/usr/bin/env python3
"""
Hardware2Code Generator
读取硬件 YAML，生成 STM32G0 + FreeRTOS 工程。
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

# 导入校验模块（注意：需确保 generator/validator.py 存在）
try:
    from validator import validate_hardware
except ImportError:
    print("Warning: validator.py not found, skipping hardware validation.")
    def validate_hardware(hw):
        return []


def load_yaml(file_path: str) -> dict:
    """加载硬件描述 YAML 文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_context(hw: dict, project_name: str) -> dict:
    """
    将 YAML 中的硬件描述处理成模板渲染所需的完整上下文。
    添加必要的默认值、计算值，并合并静态路径信息。
    """
    # 提取 mcu 信息，确保必要的字段存在并提供默认值
    mcu = hw.get("mcu", {})
    mcu["core_clock_mhz"] = int(mcu.get("core_clock_mhz", 64))
    mcu["hse_freq"] = int(mcu.get("hse_freq", 8000000))

    pins = hw.get("pins", [])
    sleep = hw.get("sleep", {})
    app_tasks = hw.get("app_tasks", [])

    # 为每个引脚补充默认的 exti 字典（避免模板中判空）
    for pin in pins:
        if pin.get("exti") is None:
            pin["exti"] = {}
        # 确保 notify_task 字段存在（即使为空）
        if "notify_task" not in pin:
            pin["notify_task"] = ""

    # 静态库绝对路径（用于 Makefile 中 HARDWARE2CODE_STATIC 变量）
    static_dir_absolute = os.path.abspath("static/stm32g0").replace("\\", "/")

    return {
        "project_name": project_name,
        "mcu": mcu,
        "pins": pins,
        "sleep": sleep,
        "app_tasks": app_tasks,
        "heap_size": hw.get("heap_size", "0x200"),
        "stack_size": hw.get("stack_size", "0x400"),
        "static_dir_absolute": static_dir_absolute,
    }


def render_templates(env: Environment, context: dict, output_dir: str):
    """渲染所有模板并写入输出目录"""
    # 创建必要的子目录
    os.makedirs(os.path.join(output_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "config"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "linker"), exist_ok=True)

    # 模板文件列表 (相对于 templates/ 目录)
    templates = {
        "src/main.c.j2": os.path.join(output_dir, "src", "main.c"),
        "src/gpio.c.j2": os.path.join(output_dir, "src", "gpio.c"),
        "src/sleep.c.j2": os.path.join(output_dir, "src", "sleep.c"),
        "src/stm32g0xx_it.c.j2": os.path.join(output_dir, "src", "stm32g0xx_it.c"),
        "config/FreeRTOSConfig.h.j2": os.path.join(output_dir, "config", "FreeRTOSConfig.h"),
        "config/stm32g0xx_hal_conf.h.j2": os.path.join(output_dir, "config", "stm32g0xx_hal_conf.h"),
        "linker/STM32G0B1RETx_FLASH.ld.j2": os.path.join(output_dir, "linker", "STM32G0B1RETx_FLASH.ld"),
        "project/Makefile.j2": os.path.join(output_dir, "Makefile"),
    }

    for template_name, out_path in templates.items():
        template = env.get_template(template_name)
        rendered = template.render(context)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out_path}")


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