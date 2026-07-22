"""
context_builder.py
构建 Jinja2 模板渲染所需的上下文变量。
"""

import os
import yaml


def load_model(model_type):
    """从 models/ 目录加载外设模型 YAML"""
    model_path = os.path.join('models', model_type + '.yaml')
    if os.path.exists(model_path):
        with open(model_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        print(f"Warning: model file for {model_type} not found.")
        return {}


def build_context(hw: dict, project_name: str) -> dict:
    """
    将 YAML 中的硬件描述处理成模板渲染所需的完整上下文。
    """
    # ---------- 基础信息提取 ----------
    mcu = hw.get("mcu", {})
    mcu["core_clock_mhz"] = int(mcu.get("core_clock_mhz", 64))
    mcu["hse_freq"] = int(mcu.get("hse_freq", 8000000))

    pins = hw.get("pins", [])
    sleep = hw.get("sleep", {})
    app_tasks = hw.get("app_tasks", [])
    business_flow = hw.get('business_flow', {})

    # ---------- 引脚字段补充默认值 ----------
    for pin in pins:
        if pin.get("exti") is None:
            pin["exti"] = {}
        if "notify_task" not in pin:
            pin["notify_task"] = ""
        if "af" not in pin:
            pin["af"] = 0

    # ---------- 外设处理 ----------
    peripherals = hw.get("peripherals", [])
    drivers = []
    hal_sources = [
        'stm32g0xx_hal.c',
        'stm32g0xx_hal_cortex.c',
        'stm32g0xx_hal_gpio.c',
        'stm32g0xx_hal_rcc.c',
        'stm32g0xx_hal_rcc_ex.c',
        'stm32g0xx_hal_pwr.c',
        'stm32g0xx_hal_pwr_ex.c',
        'stm32g0xx_hal_exti.c'
    ]

    has_i2c = False
    has_rtc = False
    has_mpu6050 = False  # 用于测试框架判断
    has_pwm = False
    has_spi = False
    has_W25Q32 = False
    
    # ---------- LED 处理 ----------
    # 检测是否定义了 LED
    has_led = any(pin.get('label') == 'LED' for pin in pins)
    # 检测是否创建了 led_task
    has_led_task = any(t.get('name') == 'led_task' for t in app_tasks)

    for p in peripherals:
        model = load_model(p['type'])
        p['model'] = model  # 将模型信息附加到外设对象上

        drivers.append({
            'name': p['name'],
            'template': model.get('driver_template', ''),
            'header_template': model.get('header_template', ''),
            'model': model,
            'peripheral': p
        })

        # 检测外设接口类型，收集需要的 HAL 源文件
        iface = model.get('interface', '').upper()
        if 'I2C' in iface:
            has_i2c = True
            if p['type'] == 'I2C_Sensor_MPU6050':
                has_mpu6050 = True
        if model.get('type') == 'Internal_RTC':
            has_rtc = True
        if 'SPI' in iface:
            has_spi = True
            if p['type'] == 'SPI_Flash_W25Q32':
                has_W25Q32 = True

    # 根据检测结果添加对应的 HAL 源文件
    if has_i2c:
        if 'stm32g0xx_hal_i2c.c' not in hal_sources:
            hal_sources.append('stm32g0xx_hal_i2c.c')
    if has_rtc:
        for rtc_file in ['stm32g0xx_hal_rtc.c', 'stm32g0xx_hal_rtc_ex.c',
                        'stm32g0xx_hal_timebase_tim.c',
                        'stm32g0xx_hal_tim.c', 'stm32g0xx_hal_tim_ex.c']:
            if rtc_file not in hal_sources:
                hal_sources.append(rtc_file)
    if has_spi:
        if 'stm32g0xx_hal_spi.c' not in hal_sources:
            hal_sources.append('stm32g0xx_hal_spi.c')
    if has_pwm:
        if 'stm32g0xx_hal_tim.c' not in hal_sources:
            hal_sources.append('stm32g0xx_hal_tim.c')
            hal_sources.append('stm32g0xx_hal_tim_ex.c')
    
    # ---------- 静态库绝对路径 ----------
    static_dir_absolute = os.path.abspath("static/stm32g0").replace("\\", "/")

    # ---------- 构建最终上下文字典 ----------
    context = {
        "project_name": project_name,
        "mcu": mcu,
        "pins": pins,
        "sleep": sleep,
        "app_tasks": app_tasks,
        "hal_sources": hal_sources,
        "peripherals": peripherals,
        "drivers": drivers,
        "has_i2c": has_i2c,
        "has_rtc": has_rtc,
        "has_pwm": has_pwm,
        "has_spi": has_spi,
        "has_mpu6050": has_mpu6050,
        "has_W25Q32": has_W25Q32,
        "has_led": has_led,
        "has_led_task": has_led_task,
        "heap_size": hw.get("heap_size", "0x200"),
        "stack_size": hw.get("stack_size", "0x400"),
        "static_dir_absolute": static_dir_absolute,
        "has_event_mgr": True,        # 始终启用事件管理器
        "has_business_flow": bool(business_flow),
        "business_flow": business_flow
    }

    return context