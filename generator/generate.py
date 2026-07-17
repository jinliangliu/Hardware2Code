#!/usr/bin/env python3
"""
Hardware2Code Generator
读取硬件 YAML，生成 STM32G0 + FreeRTOS 工程。
"""

import argparse
import os
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader


def load_yaml(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_context(hw: dict, project_name: str) -> dict:
    """
    将 YAML 中的硬件描述处理成模板渲染所需的完整上下文。
    这里只做简单映射，复杂逻辑（如引脚分组、中断计算）可后续扩展。
    """
    # 提取 mcu 信息，确保 core_clock_mhz 为数值
    mcu = hw.get("mcu", {})
    mcu["core_clock_mhz"] = int(mcu.get("core_clock_mhz", 64))
    mcu["hse_freq"] = int(mcu.get("hse_freq", 8000000))

    pins = hw.get("pins", [])
    sleep = hw.get("sleep", {})
    app_tasks = hw.get("app_tasks", [])

    # 简单检查：若按钮配置了 EXTI，自动标记
    for pin in pins:
        if pin.get("exti") is None:
            pin["exti"] = {}

    return {
        "project_name": project_name,
        "mcu": mcu,
        "pins": pins,
        "sleep": sleep,
        "app_tasks": app_tasks,
        "heap_size": hw.get("heap_size", "0x800"),
        "stack_size": hw.get("stack_size", "0x400"),
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


def copy_static_files(output_dir: str, static_dir: str = "static/stm32g0"):
    """
    如果需要把静态库复制进生成的工程（非引用模式），在此实现。
    当前 Makefile 采用相对路径引用 static/，故无需复制。
    """
    # 本示例不复制，只保留接口供将来使用
    pass


def generate(hardware_yaml: str, output_dir: str):
    # 加载硬件描述
    hw = load_yaml(hardware_yaml)
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
    render_templates(env, context, output_dir)

    # 可选：复制静态文件
    copy_static_files(output_dir)

    print(f"\nProject '{project_name}' generated successfully in '{output_dir}'")


def main():
    parser = argparse.ArgumentParser(description="Hardware2Code Generator")
    parser.add_argument("-i", "--input", required=True, help="Path to hardware YAML file")
    parser.add_argument("-o", "--output", required=True, help="Output directory for generated project")
    args = parser.parse_args()

    generate(args.input, args.output)


if __name__ == "__main__":
    main()