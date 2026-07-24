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
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML file not found: '{file_path}'")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parsing error in '{file_path}': {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading YAML file '{file_path}': {e}")


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
    boot_config = context.get("boot_config", {})
    for drv in drivers:
        if drv.get("header_template"):
            template = env.get_template(drv["header_template"])
            rendered = template.render(peripheral=drv["peripheral"], model=drv["model"],
                                       boot_config=boot_config)
            out_path = os.path.join(output_dir, "src", "drivers", f"drv_{drv['name']}.h")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(rendered)
            print(f"Generated: {out_path}")

        if drv.get("template"):
            template = env.get_template(drv["template"])
            rendered = template.render(peripheral=drv["peripheral"], model=drv["model"],
                                       boot_config=boot_config)
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
    if context.get("has_substate"):
        test_templates["test/test_substate.c.j2"] = os.path.join(test_dir, "test_substate.c")

    # Bootloader unit tests
    if context.get("has_bootloader"):
        test_templates["test/test_boot_crc.c.j2"] = os.path.join(test_dir, "test_boot_crc.c")
        test_templates["test/test_boot_nvm.c.j2"] = os.path.join(test_dir, "test_boot_nvm.c")
        test_templates["test/test_boot_jump.c.j2"] = os.path.join(test_dir, "test_boot_jump.c")

    # FOTA unit tests
    if context.get("has_fota"):
        test_templates["test/test_fota_protocol.c.j2"] = os.path.join(test_dir, "test_fota_protocol.c")
        test_templates["test/test_fota_bspatch.c.j2"] = os.path.join(test_dir, "test_fota_bspatch.c")
        
    # 状态机测试
    if context.get("has_business_flow"):
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

    # ---------- .vscode 编辑器配置 ----------
    vscode_dir = os.path.join(output_dir, ".vscode")
    os.makedirs(vscode_dir, exist_ok=True)

    vscode_templates = {
        "vscode/settings.json.j2": ".vscode/settings.json",
        "vscode/tasks.json.j2": ".vscode/tasks.json",
        "vscode/launch.json.j2": ".vscode/launch.json",
        "vscode/c_cpp_properties.json.j2": ".vscode/c_cpp_properties.json",
        "vscode/extensions.json.j2": ".vscode/extensions.json",
    }
    for tmpl_name, rel_out in vscode_templates.items():
        template = env.get_template(tmpl_name)
        rendered = template.render(context)
        out_path = os.path.join(output_dir, rel_out)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {out_path}")

    # ---------- 复制 HAL Timebase 文件到工程（效仿STM32Cube） ----------
    if context.get("has_rtc"):
        timebase_src = os.path.join("static", "stm32g0", "HAL", "Src", "stm32g0xx_hal_timebase_tim.c")
        timebase_dst = os.path.join(output_dir, "src", "stm32g0xx_hal_timebase_tim.c")
        if os.path.exists(timebase_src):
            shutil.copy2(timebase_src, timebase_dst)
            print(f"Copied stm32g0xx_hal_timebase_tim.c to src/")
        else:
            print(f"Warning: {timebase_src} not found")

    # ---------- Bootloader ----------
    if context.get("has_bootloader"):
        boot_dir = os.path.join(output_dir, "bootloader")
        os.makedirs(boot_dir, exist_ok=True)

        # Bootloader 链接脚本
        boot_ld = env.get_template("linker/bootloader.ld.j2")
        rendered = boot_ld.render(context)
        ld_path = os.path.join(output_dir, "linker", "bootloader.ld")
        with open(ld_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {ld_path}")

        # App Slot A 链接脚本
        slot_a_ld = env.get_template("linker/app_slot_a.ld.j2")
        rendered = slot_a_ld.render(context)
        ld_path = os.path.join(output_dir, "linker", "app_slot_a.ld")
        with open(ld_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {ld_path}")

        # App Slot B 链接脚本
        slot_b_ld = env.get_template("linker/app_slot_b.ld.j2")
        rendered = slot_b_ld.render(context)
        ld_path = os.path.join(output_dir, "linker", "app_slot_b.ld")
        with open(ld_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {ld_path}")

        # Bootloader 核心源文件
        boot_templates = {
            "bootloader/boot_main.c.j2": "main.c",
            "bootloader/boot_nvm.c.j2": "boot_nvm.c",
            "bootloader/boot_nvm.h.j2": "boot_nvm.h",
            "bootloader/boot_crc.c.j2": "boot_crc.c",
            "bootloader/boot_crc.h.j2": "boot_crc.h",
            "bootloader/boot_jump.c.j2": "boot_jump.c",
            "bootloader/boot_jump.h.j2": "boot_jump.h",
        }
        for tmpl_name, fname in boot_templates.items():
            template = env.get_template(tmpl_name)
            rendered = template.render(context)
            out_path = os.path.join(boot_dir, fname)
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(rendered)
            print(f"Generated: {out_path}")

        # Bootloader Makefile（独立 Makefile 在 bootloader/ 目录下）
        boot_makefile = env.get_template("project/bootloader_makefile.j2")
        rendered = boot_makefile.render(context)
        makefile_path = os.path.join(boot_dir, "Makefile")
        with open(makefile_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(rendered)
        print(f"Generated: {makefile_path}")

        # App 端启动标记文件
        boot_app_templates = {
            "bootloader/boot_app.h.j2": os.path.join(output_dir, "src", "boot_app.h"),
            "bootloader/boot_app.c.j2": os.path.join(output_dir, "src", "boot_app.c"),
        }
        for tmpl_name, out_path in boot_app_templates.items():
            template = env.get_template(tmpl_name)
            rendered = template.render(context)
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(rendered)
            print(f"Generated: {out_path}")

        # 复制 CRC 后处理脚本
        crc_script = os.path.join("generator", "patch_crc.py")
        if os.path.exists(crc_script):
            shutil.copy(crc_script, os.path.join(output_dir, "patch_crc.py"))
            print("Copied patch_crc.py")


def generate(hardware_yaml: str, output_dir: str, hil_mode: bool = False):
    print(f"\n{'='*60}")
    print(f"Hardware2Code Generator v1.0")
    print(f"{'='*60}")
    print(f"Input file:  {hardware_yaml}")
    print(f"Output dir:  {output_dir}")
    print(f"HIL mode:    {'Yes' if hil_mode else 'No'}")
    print(f"{'='*60}\n")

    try:
        hw = load_yaml(hardware_yaml)
        print("[OK] YAML file loaded successfully")
    except FileNotFoundError as e:
        print(f"[CRITICAL] {e}")
        print("\nPlease check the input file path and try again.")
        sys.exit(1)
    except ValueError as e:
        print(f"[CRITICAL] {e}")
        print("\nPlease check your YAML syntax and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    errors = validate_hardware(hw)
    if errors:
        print(f"\n{'='*60}")
        print(f"VALIDATION RESULTS")
        print(f"{'='*60}")
        
        critical_errors = [e for e in errors if e.startswith('[CRITICAL]')]
        regular_errors = [e for e in errors if e.startswith('[ERROR]')]
        warnings = [e for e in errors if e.startswith('[WARNING]')]
        infos = [e for e in errors if e.startswith('[INFO]')]

        if critical_errors:
            print("\n[CRITICAL] Fatal errors (cannot continue):")
            for err in critical_errors:
                print(f"  {err}")
        
        if regular_errors:
            print("\n[ERROR] Errors (recommended to fix):")
            for err in regular_errors:
                print(f"  {err}")
        
        if warnings:
            print("\n[WARNING] Warnings (may cause unexpected behavior):")
            for warn in warnings:
                print(f"  {warn}")
        
        if infos:
            print("\n[INFO] Information:")
            for info in infos:
                print(f"  {info}")

        if critical_errors or regular_errors:
            print(f"\n{'='*60}")
            print(f"Found {len(critical_errors)} critical errors, {len(regular_errors)} errors, {len(warnings)} warnings")
            print("Please fix the errors and try again.")
            print(f"{'='*60}")
            sys.exit(1)
        else:
            print(f"\n[OK] Validation passed with {len(warnings)} warnings")

    project_name = os.path.basename(output_dir) or "hw2code"
    
    try:
        context = build_context(hw, project_name, hil_mode)
        print("[OK] Context built successfully")
    except Exception as e:
        print(f"[ERROR] Error building context: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    try:
        env = Environment(
            loader=FileSystemLoader("templates", encoding='utf-8'),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        print("[OK] Template environment initialized")
    except Exception as e:
        print(f"[ERROR] Error initializing template environment: {e}")
        sys.exit(1)

    try:
        if hil_mode:
            render_hil_project(env, context, output_dir)
        else:
            render_templates(env, context, output_dir)
    except Exception as e:
        print(f"\n[ERROR] Error during template rendering: {e}")
        import traceback
        traceback.print_exc()
        print("\nPossible causes:")
        print("  - Missing template file")
        print("  - Invalid context variable")
        print("  - Jinja2 template syntax error")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"SUCCESS! Project '{project_name}' generated in '{output_dir}'")
    print(f"{'='*60}")
    print("\nNext steps:")
    print(f"  1. cd {output_dir}")
    print(f"  2. make")
    print(f"  3. make flash")
    print(f"\nTo run tests:")
    print(f"  cd {output_dir}/test")
    print(f"  python run_tests.py")


def main():
    parser = argparse.ArgumentParser(description="Hardware2Code Generator")
    parser.add_argument("-i", "--input", required=True, help="Path to hardware YAML file")
    parser.add_argument("-o", "--output", required=True, help="Output directory for generated project")
    parser.add_argument("--hil", action="store_true", help="Generate HIL test firmware")
    args = parser.parse_args()

    generate(args.input, args.output, args.hil)


if __name__ == "__main__":
    main()