#!/usr/bin/env python3
"""
Hardware2Code Generator
读取硬件 YAML，生成 STM32G0 + FreeRTOS 工程（或 HIL 测试固件）。
"""

import argparse
import difflib
import logging
import os
import sys
import shutil
import tempfile
from typing import Callable

import jinja2
import yaml
from jinja2 import Environment, FileSystemLoader

from context.builder import build_context
from validator import validate_hardware
from jinja_filters import register_filters
from models import HardwareModel
from paths import STATIC_UNITY_DIR, HIL_RUNNER_PATH, RUN_TESTS_PATH, PATCH_CRC_PATH, TIMEBASE_SRC, TEMPLATES_DIR

logger = logging.getLogger("hw2c")


def _setup_logging(verbose: bool = False):
    """Configure logging with level based on --verbose flag."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
    logging.root.handlers.clear()
    logging.root.addHandler(handler)
    logging.root.setLevel(level)
    logger.setLevel(level)


def _write_file(out_path: str, content: str, dry_run: bool, show_diff: bool):
    """Write rendered content to file. In dry-run mode, skip writing.
    In diff mode, show unified diff against existing file.
    """
    rel_path = out_path

    if dry_run:
        logger.info(f"[DRY-RUN] Would generate: {rel_path}")
        return

    if show_diff and os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            old_content = f.read()
        if old_content != content:
            diff = difflib.unified_diff(
                old_content.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{os.path.basename(out_path)}",
                tofile=f"b/{os.path.basename(out_path)}",
            )
            diff_text = "".join(diff)
            if diff_text:
                logger.info(f"Diff for {rel_path}:\n{diff_text}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    logger.info(f"Generated: {rel_path}")


def load_yaml(file_path: str) -> dict:
    """加载硬件描述 YAML 文件"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML file not found: '{file_path}'")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parsing error in '{file_path}': {e}")
    except OSError as e:
        raise RuntimeError(f"Error loading YAML file '{file_path}': {e}")


def render_hil_project(env: Environment, context: dict, output_dir: str,
                       dry_run: bool = False, show_diff: bool = False):
    """渲染 HIL 测试固件工程"""
    if not dry_run:
        os.makedirs(os.path.join(output_dir, "src", "drivers"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "config"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "linker"), exist_ok=True)

    # 复制 Unity 源文件
    unity_src = STATIC_UNITY_DIR
    if os.path.exists(unity_src):
        if not dry_run:
            shutil.copytree(unity_src, os.path.join(output_dir, "unity"), dirs_exist_ok=True)
        logger.info("Copied Unity to unity/")
    else:
        logger.warning("static/unity not found. HIL tests will not compile.")

    # 生成 HIL 主固件
    hil_main = env.get_template("test/hil_test.c.j2")
    rendered = hil_main.render(context)
    _write_file(os.path.join(output_dir, "src", "main.c"), rendered, dry_run, show_diff)

    # 生成必要的标准文件
    standard = {
        "config/stm32g0xx_hal_conf.h.j2": os.path.join(output_dir, "config", "stm32g0xx_hal_conf.h"),
        "linker/STM32G0B1RETx_FLASH.ld.j2": os.path.join(output_dir, "linker", "STM32G0B1RETx_FLASH.ld"),
        "project/Makefile.j2": os.path.join(output_dir, "Makefile"),
    }
    for tmpl, out in standard.items():
        template = env.get_template(tmpl)
        rendered = template.render(context)
        _write_file(out, rendered, dry_run, show_diff)

    # 复制 hil_runner.py
    hil_runner_src = HIL_RUNNER_PATH
    if os.path.exists(hil_runner_src):
        if not dry_run:
            shutil.copy(hil_runner_src, os.path.join(output_dir, "hil_runner.py"))
        logger.info("Copied hil_runner.py")
    else:
        logger.warning("generator/hil_runner.py not found")

    logger.info(f"HIL project '{os.path.basename(output_dir)}' generated successfully.")


def render_templates(env: Environment, context: dict, output_dir: str,
                     dry_run: bool = False, show_diff: bool = False):
    """渲染所有模板并写入输出目录，包括测试框架"""
    if not dry_run:
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
        _write_file(out_path, rendered, dry_run, show_diff)

    # ---------- 事件管理器 ----------
    event_mgr_templates = {
        "src/event_mgr.h.j2": os.path.join(output_dir, "src", "event_mgr.h"),
        "src/event_mgr.c.j2": os.path.join(output_dir, "src", "event_mgr.c"),
    }
    for tmpl_name, out_path in event_mgr_templates.items():
        template = env.get_template(tmpl_name)
        rendered = template.render(context)
        _write_file(out_path, rendered, dry_run, show_diff)

    # ---------- 日志子系统（全局，非外设驱动） ----------
    if context.get("has_log"):
        log_templates = {
            "drivers/drv_log.h.j2": os.path.join(output_dir, "src", "drivers", "drv_log.h"),
            "drivers/drv_log.c.j2": os.path.join(output_dir, "src", "drivers", "drv_log.c"),
        }
        for tmpl_name, out_path in log_templates.items():
            template = env.get_template(tmpl_name)
            rendered = template.render(context)
            _write_file(out_path, rendered, dry_run, show_diff)

    # ---------- 外设驱动 ----------
    drivers = context.get("drivers", [])
    boot_config = context.get("boot_config", {})
    for drv in drivers:
        driver_ctx = dict(context)
        driver_ctx["peripheral"] = drv["peripheral"]
        driver_ctx["model"] = drv["model"]
        driver_ctx["boot_config"] = boot_config

        if drv.get("header_template"):
            template = env.get_template(drv["header_template"])
            rendered = template.render(**driver_ctx)
            out_path = os.path.join(output_dir, "src", "drivers", f"drv_{drv['name']}.h")
            _write_file(out_path, rendered, dry_run, show_diff)

        if drv.get("template"):
            template = env.get_template(drv["template"])
            rendered = template.render(**driver_ctx)
            out_path = os.path.join(output_dir, "src", "drivers", f"drv_{drv['name']}.c")
            _write_file(out_path, rendered, dry_run, show_diff)

    # ---------- 业务状态机 ----------
    if context.get("has_business_flow"):
        state_machine_templates = {
            "app/statemachine.h.j2": os.path.join(output_dir, "src", "statemachine.h"),
            "app/statemachine.c.j2": os.path.join(output_dir, "src", "statemachine.c"),
        }
        for tmpl_name, out_path in state_machine_templates.items():
            template = env.get_template(tmpl_name)
            rendered = template.render(context)
            _write_file(out_path, rendered, dry_run, show_diff)

    # ---------- 测试框架 ----------
    test_dir = os.path.join(output_dir, "test")
    if not dry_run:
        os.makedirs(test_dir, exist_ok=True)

    # 复制 Unity
    unity_src = STATIC_UNITY_DIR
    if os.path.exists(unity_src):
        if not dry_run:
            shutil.copytree(unity_src, os.path.join(test_dir, "unity"), dirs_exist_ok=True)
        logger.info("Copied Unity framework to test/unity/")
    else:
        logger.warning("static/unity not found. Tests will not compile without Unity.")

    # Mock HAL
    mock_templates = {
        "test/mock_hal.h.j2": os.path.join(test_dir, "mock_hal.h"),
        "test/mock_hal.c.j2": os.path.join(test_dir, "mock_hal.c"),
    }
    for tmpl_name, out_path in mock_templates.items():
        template = env.get_template(tmpl_name)
        rendered = template.render(context)
        _write_file(out_path, rendered, dry_run, show_diff)

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

    for p in context.get("peripherals", []):
        if p.get("type") == "I2C_EEPROM":
            test_templates["test/test_eeprom.c.j2"] = os.path.join(test_dir, "test_eeprom.c")
            break

    if context.get("has_spi_flash"):
        test_templates["test/test_spi_flash.c.j2"] = os.path.join(test_dir, "test_spi_flash.c")

    if context.get("has_pwm"):
        test_templates["test/test_pwm.c.j2"] = os.path.join(test_dir, "test_pwm.c")

    if context.get("has_adc"):
        test_templates["test/test_adc.c.j2"] = os.path.join(test_dir, "test_adc.c")

    if context.get("has_uart"):
        test_templates["test/test_uart.c.j2"] = os.path.join(test_dir, "test_uart.c")
    if context.get("has_ir"):
        test_templates["test/test_ir.c.j2"] = os.path.join(test_dir, "test_ir.c")
    if context.get("has_cellular"):
        test_templates["test/test_cellular.c.j2"] = os.path.join(test_dir, "test_cellular.c")
    if context.get("has_rs485"):
        test_templates["test/test_rs485.c.j2"] = os.path.join(test_dir, "test_rs485.c")
    if context.get("has_modbus"):
        test_templates["test/test_modbus.c.j2"] = os.path.join(test_dir, "test_modbus.c")
    if context.get("has_mqtt"):
        test_templates["test/test_mqtt.c.j2"] = os.path.join(test_dir, "test_mqtt.c")
    if context.get("has_cli"):
        test_templates["test/test_cli.c.j2"] = os.path.join(test_dir, "test_cli.c")
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
        _write_file(out_path, rendered, dry_run, show_diff)

    # 复制 run_tests.py
    run_tests_script = RUN_TESTS_PATH
    if os.path.exists(run_tests_script):
        if not dry_run:
            shutil.copy(run_tests_script, os.path.join(test_dir, "run_tests.py"))
        logger.info("Copied run_tests.py to test/")
    else:
        logger.warning("run_tests.py not found in generator/. Tests will not be executable via make test.")

    # ---------- .vscode 编辑器配置 ----------
    vscode_dir = os.path.join(output_dir, ".vscode")
    if not dry_run:
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
        _write_file(out_path, rendered, dry_run, show_diff)

    # ---------- 复制 HAL Timebase 文件到工程 ----------
    if context.get("has_rtc"):
        timebase_src = TIMEBASE_SRC
        timebase_dst = os.path.join(output_dir, "src", "stm32g0xx_hal_timebase_tim.c")
        if os.path.exists(timebase_src):
            if not dry_run:
                shutil.copy2(timebase_src, timebase_dst)
            logger.info("Copied stm32g0xx_hal_timebase_tim.c to src/")
        else:
            logger.warning(f"{timebase_src} not found")

    # ---------- Bootloader ----------
    if context.get("has_bootloader"):
        boot_dir = os.path.join(output_dir, "bootloader")
        if not dry_run:
            os.makedirs(boot_dir, exist_ok=True)

        # Bootloader 链接脚本
        boot_ld = env.get_template("linker/bootloader.ld.j2")
        rendered = boot_ld.render(context)
        _write_file(os.path.join(output_dir, "linker", "bootloader.ld"), rendered, dry_run, show_diff)

        # App Slot A 链接脚本
        slot_a_ld = env.get_template("linker/app_slot_a.ld.j2")
        rendered = slot_a_ld.render(context)
        _write_file(os.path.join(output_dir, "linker", "app_slot_a.ld"), rendered, dry_run, show_diff)

        # App Slot B 链接脚本
        slot_b_ld = env.get_template("linker/app_slot_b.ld.j2")
        rendered = slot_b_ld.render(context)
        _write_file(os.path.join(output_dir, "linker", "app_slot_b.ld"), rendered, dry_run, show_diff)

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
            _write_file(out_path, rendered, dry_run, show_diff)

        # Bootloader Makefile
        boot_makefile = env.get_template("project/bootloader_makefile.j2")
        rendered = boot_makefile.render(context)
        _write_file(os.path.join(boot_dir, "Makefile"), rendered, dry_run, show_diff)

        # App 端启动标记文件
        boot_app_templates = {
            "bootloader/boot_app.h.j2": os.path.join(output_dir, "src", "boot_app.h"),
            "bootloader/boot_app.c.j2": os.path.join(output_dir, "src", "boot_app.c"),
        }
        for tmpl_name, out_path in boot_app_templates.items():
            template = env.get_template(tmpl_name)
            rendered = template.render(context)
            _write_file(out_path, rendered, dry_run, show_diff)

        # 复制 CRC 后处理脚本
        crc_script = PATCH_CRC_PATH
        if os.path.exists(crc_script):
            if not dry_run:
                shutil.copy(crc_script, os.path.join(output_dir, "patch_crc.py"))
            logger.info("Copied patch_crc.py")


def generate_project(
    yaml_path: str,
    output_dir: str,
    hil_mode: bool = False,
    dry_run: bool = False,
    show_diff: bool = False,
    validate_fn: Callable[[dict], list] = validate_hardware,
    build_context_fn: Callable[[dict, str, bool], dict] = build_context,
    load_yaml_fn: Callable[[str], dict] = load_yaml,
) -> None:
    banner = "=" * 60
    logger.info(f"\n{banner}")
    logger.info("Hardware2Code Generator v1.0")
    logger.info(banner)
    logger.info(f"Input file:  {yaml_path}")
    logger.info(f"Output dir:  {output_dir}")
    logger.info(f"HIL mode:    {'Yes' if hil_mode else 'No'}")
    logger.info(f"Dry run:     {'Yes' if dry_run else 'No'}")
    if show_diff:
        logger.info(f"Diff mode:   Yes")
    logger.info(f"{banner}")

    # Dry-run: redirect to temp directory
    if dry_run:
        output_dir = os.path.join(tempfile.gettempdir(), "hw2c_dryrun", os.path.basename(output_dir))
        logger.info(f"Dry-run output: {output_dir}")

    try:
        hw_raw = load_yaml_fn(yaml_path)
        logger.info("[OK] YAML file loaded successfully")
    except FileNotFoundError as e:
        logger.critical(str(e))
        sys.exit(1)
    except ValueError as e:
        logger.critical(str(e))
        sys.exit(1)
    except (yaml.YAMLError, OSError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    # ---------- Pydantic model validation (type / shape / constraints) ----------
    try:
        hw_model = HardwareModel.model_validate(hw_raw)
        hw = hw_model.model_dump(exclude_none=True)
        logger.info("[OK] Pydantic model validation passed")
    except Exception as e:
        logger.critical(f"Schema validation failed: {e}")
        sys.exit(1)

    # ---------- Cross-field business logic validation ----------
    errors = validate_fn(hw)
    if errors:
        logger.info(f"\n{banner}")
        logger.info("VALIDATION RESULTS")
        logger.info(banner)

        critical_errors = [e for e in errors if e['severity'] == 'CRITICAL']
        regular_errors = [e for e in errors if e['severity'] == 'ERROR']
        warnings = [e for e in errors if e['severity'] == 'WARNING']
        infos = [e for e in errors if e['severity'] == 'INFO']

        if critical_errors:
            logger.info("\n[CRITICAL] Fatal errors (cannot continue):")
            for err in critical_errors:
                logger.critical(f"  {err['message']}")

        if regular_errors:
            logger.info("\n[ERROR] Errors (recommended to fix):")
            for err in regular_errors:
                logger.error(f"  {err['message']}")

        if warnings:
            logger.info("\n[WARNING] Warnings (may cause unexpected behavior):")
            for warn in warnings:
                logger.warning(f"  {warn['message']}")

        if infos:
            logger.info("\n[INFO] Information:")
            for info in infos:
                logger.info(f"  {info['message']}")

        if critical_errors or regular_errors:
            logger.info(f"\n{banner}")
            logger.info(f"Found {len(critical_errors)} critical, {len(regular_errors)} errors, {len(warnings)} warnings")
            logger.info("Please fix the errors and try again.")
            logger.info(banner)
            sys.exit(1)
        else:
            logger.info(f"\n[OK] Validation passed with {len(warnings)} warnings")
    else:
        logger.info("[OK] Hardware validation passed")

    project_name = os.path.basename(output_dir) or "hw2code"

    try:
        context = build_context_fn(hw, project_name, hil_mode)
        logger.info("[OK] Context built successfully")
    except (yaml.YAMLError, FileNotFoundError, ValueError) as e:
        logger.error(f"Error building context: {e}")
        sys.exit(1)
    except (ValueError, KeyError, RuntimeError) as e:
        logger.error(f"Unexpected error building context: {e}")
        logger.debug("", exc_info=True)
        sys.exit(1)

    try:
        env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR, encoding='utf-8'),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        register_filters(env)
        logger.info("[OK] Template environment initialized")
    except (jinja2.TemplateError, OSError) as e:
        logger.error(f"Error initializing template environment: {e}")
        sys.exit(1)

    try:
        if hil_mode:
            render_hil_project(env, context, output_dir, dry_run, show_diff)
        else:
            render_templates(env, context, output_dir, dry_run, show_diff)
    except jinja2.TemplateNotFound as e:
        logger.error(f"Template file not found: {e}")
        sys.exit(1)
    except jinja2.TemplateError as e:
        logger.error(f"Jinja2 template error: {e}")
        sys.exit(1)
    except (jinja2.TemplateError, OSError, KeyError) as e:
        logger.error(f"Unexpected error during template rendering: {e}")
        logger.debug("", exc_info=True)
        sys.exit(1)

    logger.info(f"\n{banner}")
    logger.info(f"SUCCESS! Project '{project_name}' generated in '{output_dir}'")
    logger.info(banner)
    logger.info("\nNext steps:")
    logger.info(f"  1. cd {output_dir}")
    logger.info(f"  2. make")
    logger.info(f"  3. make flash")
    logger.info(f"\nTo run tests:")
    logger.info(f"  cd {output_dir}/test")
    logger.info(f"  python run_tests.py")


def generate(hardware_yaml: str, output_dir: str, hil_mode: bool = False,
             dry_run: bool = False, show_diff: bool = False):
    """Backward-compatible wrapper around generate_project with default deps."""
    return generate_project(hardware_yaml, output_dir, hil_mode, dry_run, show_diff)


def main():
    parser = argparse.ArgumentParser(
        description="Hardware2Code Generator - Generate STM32G0 + FreeRTOS projects from YAML"
    )
    parser.add_argument("-i", "--input", required=True, help="Path to hardware YAML file")
    parser.add_argument("-o", "--output", required=True, help="Output directory for generated project")
    parser.add_argument("--hil", action="store_true", help="Generate HIL test firmware")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate to temp dir, show what would be created (no disk write)")
    parser.add_argument("--diff", action="store_true",
                        help="Show unified diff against existing files")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug-level logging")
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)

    generate(args.input, args.output, args.hil,
             dry_run=args.dry_run, show_diff=args.diff)


if __name__ == "__main__":
    main()
