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


def build_context(hw: dict, project_name: str, hil_mode: bool = False) -> dict:
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
    has_mpu6050 = False
    has_pwm = False
    has_spi = False
    has_spi_flash = False
    has_adc = False
    has_uart = False

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
                has_spi_flash = True
        if model.get('type') == 'Internal_PWM':
            has_pwm = True
        if model.get('type') == 'Internal_ADC':
            has_adc = True
        if model.get('type') == 'UART_Serial':
            has_uart = True

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
    if has_adc:
        if 'stm32g0xx_hal_adc.c' not in hal_sources:
            hal_sources.append('stm32g0xx_hal_adc.c')
    if has_uart or hil_mode:
        if 'stm32g0xx_hal_uart.c' not in hal_sources:
            hal_sources.append('stm32g0xx_hal_uart.c')

    # ---------- 业务逻辑 DSL ----------
    business_flow = hw.get('business_flow', {})
    has_business_flow = bool(business_flow)

    # 检测是否有 LED 引脚和 led_task
    has_led = any(pin.get('label') == 'LED' for pin in pins)
    has_led_task = any(t.get('name') == 'led_task' for t in app_tasks)

    # ---------- 确保每个复合状态都有 initial_state ----------
    def fix_initial_state(states):
        for s in states:
            if s.get('states'):
                if not s.get('initial_state'):
                    s['initial_state'] = s['states'][0]['name']
                # 递归修复子状态
                fix_initial_state(s['states'])

        # ---------- 状态机引用处理 ----------
    def resolve_ref(state, base_path):
        """如果状态是引用，加载外部文件并返回其业务流定义"""
        if state.get('type') != 'ref':
            return state
        ref_file = state.get('ref')
        if not ref_file:
            print("Warning: ref state without ref file")
            return state
        ref_path = os.path.join('examples', ref_file)  # 假设引用文件在 examples/ 下
        if not os.path.exists(ref_path):
            ref_path = ref_file  # 尝试直接路径
        try:
            with open(ref_path, 'r', encoding='utf-8') as f:
                ref_data = yaml.safe_load(f)
            # 提取被引用的业务流（假设文件顶层是 business_flow）
            ref_flow = ref_data.get('business_flow')
            if not ref_flow:
                print(f"Warning: no business_flow found in {ref_file}")
                return state
            # 将引用流的 states 合并到当前状态（作为子状态）
            # 保留当前状态的其他属性（name, transitions等），但 states 从引用获取
            new_state = dict(state)  # 复制
            new_state.pop('type', None)
            new_state.pop('ref', None)
            new_state['states'] = ref_flow.get('states', [])
            new_state['initial_state'] = ref_flow.get('initial_state', new_state['states'][0]['name'] if new_state['states'] else None)
            # 合并变量：引用流变量应带有前缀以避免冲突，但为简单，直接合并（用户需自行避免冲突）
            if ref_flow.get('variables'):
                if 'variables' not in new_state:
                    new_state['variables'] = []
                new_state['variables'].extend(ref_flow['variables'])
            return new_state
        except Exception as e:
            print(f"Error loading ref {ref_file}: {e}")
            return state

    def resolve_all_refs(states):
        for i, s in enumerate(states):
            if s.get('type') == 'ref':
                states[i] = resolve_ref(s, '')
            if s.get('states'):
                resolve_all_refs(s['states'])

    if business_flow:
        if business_flow.get('states'):
            resolve_all_refs(business_flow['states'])
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                resolve_all_refs(region['states'])

    # 检查是否有子状态
    def has_nested_states(states):
        for s in states:
            if s.get('states'):
                return True
        return False

    has_substate = False
    if business_flow:
        if business_flow.get('states'):
            has_substate = has_nested_states(business_flow['states'])
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                if has_nested_states(region['states']):
                    has_substate = True
                    break

    # ---------- HIL 配置 ----------
    hil_config = hw.get('hil', {})
    if not hil_config:
        hil_config = {
            'baudrate': 115200,
            'uart': 'UART2',
            'tx_pin': 'PA2',
            'rx_pin': 'PA3'
        }

    # 生成 HIL 测试用例列表
    hil_tests = []
    for p in peripherals:
        if p['type'] == 'Internal_RTC':
            hil_tests.append({
                'name': 'test_RTC_Init',
                'body': r"""
    RTC_HandleTypeDef hrtc;
    __HAL_RCC_RTC_ENABLE();
    HAL_PWR_EnableBkUpAccess();

    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_LSE | RCC_OSCILLATORTYPE_LSI;
    RCC_OscInitStruct.LSEState = RCC_LSE_ON;
    RCC_OscInitStruct.LSIState = RCC_LSI_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        RCC_OscInitStruct.LSEState = RCC_LSE_OFF;
        HAL_RCC_OscConfig(&RCC_OscInitStruct);
    }

    RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};
    PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_RTC;
    PeriphClkInit.RTCClockSelection = (RCC_OscInitStruct.LSEState == RCC_LSE_ON) ?
                                       RCC_RTCCLKSOURCE_LSE : RCC_RTCCLKSOURCE_LSI;
    HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit);

    __HAL_RCC_RTC_ENABLE();

    hrtc.Instance = RTC;
    hrtc.Init.HourFormat = RTC_HOURFORMAT_24;
    hrtc.Init.AsynchPrediv = 127;
    hrtc.Init.SynchPrediv = 255;
    hrtc.Init.OutPut = RTC_OUTPUT_DISABLE;
    if (HAL_RTC_Init(&hrtc) != HAL_OK) {
        TEST_FAIL("HAL_RTC_Init failed");
    } else {
        TEST_PASS();
    }
"""
            })
    if not hil_tests:
        hil_tests.append({
            'name': 'test_dummy',
            'body': 'TEST_PASS();'
        })

    # ---------- Defer 动作处理 ----------
    defer_actions = []
    defer_counter = 0

    def process_defer(action_list, defer_counter):
        new_actions = []
        for act in action_list:
            if act.startswith('defer '):
                parts = act.split('=>', 1)
                if len(parts) == 2:
                    time_part = parts[0].strip().split()
                    if len(time_part) >= 2:
                        time_ms = time_part[1]
                        sub_action = parts[1].strip()
                        timer_name = f"defer_{defer_counter}"
                        new_actions.append(f"start_timer {timer_name} {time_ms}")
                        defer_actions.append({
                            'timer_name': timer_name,
                            'sub_action': sub_action
                        })
                        defer_counter += 1
                        continue
            new_actions.append(act)
        return new_actions, defer_counter

    def traverse_states(states, defer_counter):
        for state in states:
            for trans in state.get('transitions', []):
                new_acts, defer_counter = process_defer(trans.get('actions', []), defer_counter)
                trans['actions'] = new_acts
            if 'on_entry' in state:
                new_acts, defer_counter = process_defer(state['on_entry'], defer_counter)
                state['on_entry'] = new_acts
            if 'on_exit' in state:
                new_acts, defer_counter = process_defer(state['on_exit'], defer_counter)
                state['on_exit'] = new_acts
            if 'states' in state:
                defer_counter = traverse_states(state['states'], defer_counter)
        return defer_counter

    if business_flow:
        if business_flow.get('states'):
            traverse_states(business_flow['states'], 0)
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                traverse_states(region['states'], 0)

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
        "has_spi_flash": has_spi_flash,
        "has_mpu6050": has_mpu6050,
        "has_adc": has_adc,
        "has_uart": has_uart,
        "has_led": has_led,
        "has_led_task": has_led_task,
        "has_business_flow": has_business_flow,
        "business_flow": business_flow,
        "has_substate": has_substate,
        "hil": hil_config,
        "hil_tests": hil_tests,
        "hil_mode": hil_mode,
        "heap_size": hw.get("heap_size", "0x200"),
        "stack_size": hw.get("stack_size", "0x400"),
        "static_dir_absolute": static_dir_absolute,
        "has_event_mgr": True,
        "defer_actions": defer_actions,
    }

    return context