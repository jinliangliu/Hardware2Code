"""
builder.py
Aggregation entry point for building the complete Jinja2 template context.
Delegates to sub-modules: pin_context, peripheral_context, hal_context,
bootloader_context.
"""

import os
import sys
import yaml
import importlib.util

from paths import MODELS_DIR, EXAMPLES_DIR, STATIC_STM32_DIR

from context.pin_context import process_pins
from context.peripheral_context import detect_peripherals
from context.bearer_context import associate_bearers
from context.hal_context import compute_hal_sources
from context.bootloader_context import build_boot_config, inject_bootloader_drivers

# Load generator/types.py with explicit module name to avoid collision
# with Python's stdlib 'types' module which is frozen at interpreter startup.
_types_spec = importlib.util.spec_from_file_location(
    "hw2c_types",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "types.py")
)
_types_module = importlib.util.module_from_spec(_types_spec)
_types_spec.loader.exec_module(_types_module)
BuildContext = _types_module.BuildContext


def load_model(model_type: str) -> dict:
    """从 models/ 目录加载外设模型 YAML"""
    model_path = os.path.join(MODELS_DIR, model_type + '.yaml')
    if os.path.exists(model_path):
        with open(model_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        print(f"Warning: model file for {model_type} not found.")
        return {}


def build_context(hw: dict, project_name: str, hil_mode: bool = False) -> BuildContext:
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
    process_pins(pins)

    # ---------- 外设处理 ----------
    peripherals = hw.get("peripherals", [])
    peri_result = detect_peripherals(peripherals, load_model)

    drivers = peri_result["drivers"]
    has_i2c = peri_result["has_i2c"]
    has_rtc = peri_result["has_rtc"]
    has_mpu6050 = peri_result["has_mpu6050"]
    has_pwm = peri_result["has_pwm"]
    has_spi = peri_result["has_spi"]
    has_spi_flash = peri_result["has_spi_flash"]
    has_adc = peri_result["has_adc"]
    has_uart = peri_result["has_uart"]
    has_rs485 = peri_result["has_rs485"]
    has_ir = peri_result["has_ir"]
    has_cellular = peri_result["has_cellular"]
    has_cli = peri_result["has_cli"]
    uart_name = peri_result["uart_name"]
    rs485_name = peri_result["rs485_name"]
    cli_uart_name = peri_result["cli_uart_name"]

    # ---------- Bearer association (MQTT/Modbus) ----------
    bearer_result = associate_bearers(peripherals, drivers)
    has_modbus = bearer_result["has_modbus"]
    has_mqtt = bearer_result["has_mqtt"]
    modbus_name = bearer_result["modbus_name"]

    # ---------- HAL sources ----------
    hal_sources = compute_hal_sources(peri_result, hil_mode)

    # ---------- Bootloader ----------
    boot_config, has_bootloader = build_boot_config(hw.get('bootloader', {}))
    boot_result = inject_bootloader_drivers(has_bootloader, has_uart,
                                             boot_config, uart_name)
    drivers.extend(boot_result['drivers_additions'])
    has_fota = boot_result['has_fota']
    for hal_file in boot_result['hal_additions']:
        if hal_file not in hal_sources:
            hal_sources.append(hal_file)

    # IWDG HAL source is auto-injected when bootloader is enabled
    if has_bootloader:
        if 'stm32g0xx_hal_iwdg.c' not in hal_sources:
            hal_sources.append('stm32g0xx_hal_iwdg.c')

    # ---------- 业务逻辑 DSL ----------
    business_flow = hw.get('business_flow', {})
    has_business_flow = bool(business_flow)

    has_led = any(pin.get('label') == 'LED' for pin in pins)
    has_led_task = any(t.get('name') == 'led_task' for t in app_tasks)

    # ---------- Log subsystem (USART2 ring-buffer logging) ----------
    log_config = hw.get('log', {})
    has_log = log_config.get('enable', False)

    # ---------- Tickless idle (requires FreeRTOS app_tasks + RTC) ----------
    has_tickless = bool(app_tasks) and has_rtc

    # ---------- 辅助函数：加载外部引用 ----------
    def load_external_flow(ref_path):
        full_path = os.path.join(EXAMPLES_DIR, ref_path)
        if not os.path.exists(full_path):
            full_path = ref_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            if data and 'business_flow' in data:
                return data['business_flow']
        except (yaml.YAMLError, OSError) as e:
            print(f"Warning: cannot load ref {ref_path}: {e}")
        return None

    # ---------- 函数：为状态和变量添加命名空间前缀 ----------
    def apply_namespace(state, namespace, _parent_vars=None):
        """Apply namespace prefix to state names, variable names, and action
        references. Recursively walks substates, carrying parent variables so
        that calc/when/guard expressions in nested transitions are rewritten
        correctly."""
        # Collect all visible variables (current state + parent scope)
        all_vars = list(_parent_vars or [])
        if 'variables' in state:
            for var in state['variables']:
                var['name'] = f"{namespace}_{var['name']}"
            all_vars.extend(state['variables'])
        if 'initial_state' in state:
            state['initial_state'] = f"{namespace}_{state['initial_state']}"

        def replace_in_actions(actions):
            import re
            for i, act in enumerate(actions):
                for var in all_vars:
                    original_name = var['name'].replace(f"{namespace}_", "")
                    pattern = r'\b' + re.escape(original_name) + r'\b'
                    act = re.sub(pattern, var['name'], act)
                actions[i] = act
        for trans in state.get('transitions', []):
            replace_in_actions(trans.get('actions', []))
        if 'on_entry' in state:
            replace_in_actions(state['on_entry'])
        if 'on_exit' in state:
            replace_in_actions(state['on_exit'])

        if 'states' in state:
            for substate in state['states']:
                substate['name'] = f"{namespace}_{substate['name']}"
                for trans in substate.get('transitions', []):
                    trans['target'] = f"{namespace}_{trans['target']}"
                apply_namespace(substate, namespace, all_vars)

    # ---------- 函数：解析单个引用状态 ----------
    def resolve_ref(state, base_path=''):
        if state.get('type') != 'ref':
            return state
        ref_file = state.get('ref')
        if not ref_file:
            return state
        flow = load_external_flow(ref_file)
        if not flow:
            return state
        new_state = {
            'name': state['name'],
            'initial_state': flow.get('initial_state'),
            'states': flow.get('states', []),
            'variables': flow.get('variables', []),
            'transitions': state.get('transitions', []),
            'on_entry': state.get('on_entry', []),
            'on_exit': state.get('on_exit', []),
            'after': state.get('after', None),
            'history': state.get('history', False),
        }
        namespace = state.get('namespace')
        if namespace:
            apply_namespace(new_state, namespace)
        return new_state

    # ---------- 递归解析所有引用 ----------
    def resolve_all_refs(states, max_depth=5):
        for _ in range(max_depth):
            changed = False
            for i, s in enumerate(states):
                if s.get('type') == 'ref':
                    states[i] = resolve_ref(s)
                    changed = True
                if states[i].get('states'):
                    resolve_all_refs(states[i]['states'], max_depth - 1)
            if not changed:
                break

    if business_flow:
        if business_flow.get('states'):
            resolve_all_refs(business_flow['states'])
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                resolve_all_refs(region['states'])

    # ---------- 确保复合状态有 initial_state ----------
    def fix_initial_state(states):
        for s in states:
            if s.get('states') and not s.get('initial_state'):
                s['initial_state'] = s['states'][0]['name']
            if s.get('states'):
                fix_initial_state(s['states'])

    if business_flow:
        if business_flow.get('states'):
            fix_initial_state(business_flow['states'])
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                fix_initial_state(region['states'])

    # ---------- 检查是否有子状态 ----------
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

    # ---------- Dict-format action normalization ----------
    # Convert new dict-format actions to legacy string format before processing.
    def normalize_dict_action(action):
        """
        Convert dict-format action to string format.
        E.g. {defer: {after: 3000, do: toggle_led}} -> "defer 3000 => toggle_led"
             {start_timer: {name: exit_timer, ms: 3000}} -> "start_timer exit_timer 3000"
             {timeline: [{ms: 1000, do: toggle_led}]} -> "timeline: 1000=>toggle_led"
        Returns the same string if already a string.
        """
        if isinstance(action, str):
            return action
        if not isinstance(action, dict):
            return str(action)

        keys = list(action.keys())
        if len(keys) != 1:
            return str(action)
        name = keys[0]
        params = action[name]

        # Simple actions (no params): toggle_led, return
        if name in ('toggle_led', 'return', 'EVENT_NONE'):
            return name

        if params is None:
            return name

        if name == 'defer':
            return f"defer {params.get('after', 0)} => {params.get('do', '')}"
        elif name == 'start_timer':
            return f"start_timer {params.get('name', '')} {params.get('ms', 0)}"
        elif name == 'stop_timer':
            return f"stop_timer {params.get('name', '')}"
        elif name == 'set':
            if 'op' in params:
                return f"set {params.get('var', '')} {params.get('op', 'inc')}"
            return f"set {params.get('var', '')} {params.get('value', 0)}"
        elif name == 'calc':
            return f"calc {params.get('var', '')} = {params.get('expr', '')}"
        elif name == 'publish':
            return f"publish {params.get('event', '')}"
        elif name == 'publish_async':
            return f"publish_async {params.get('event', '')}"
        elif name == 'when':
            return f"when {params.get('cond', '')} => {params.get('do', '')}"
        elif name == 'send_to':
            return f"send_to {params.get('region', '')} {params.get('event', '')}"
        elif name == 'timeline':
            if isinstance(params, list):
                parts = [f"{item.get('ms', 0)}=>{item.get('do', '')}" for item in params]
                return "timeline: " + ", ".join(parts)
            return name
        else:
            return name

    def normalize_actions(action_list):
        """Normalize all actions in a list, converting dicts to strings."""
        if not action_list:
            return
        for i, act in enumerate(action_list):
            action_list[i] = normalize_dict_action(act)

    # Apply normalization to all action lists in business_flow
    def traverse_and_normalize(states_or_regions):
        """Walk all states/regions and normalize action lists."""
        entries = states_or_regions if isinstance(states_or_regions, list) else [states_or_regions]
        for entry in entries:
            # States list
            for state in entry.get('states', []):
                if state.get('on_entry'):
                    normalize_actions(state['on_entry'])
                if state.get('on_exit'):
                    normalize_actions(state['on_exit'])
                for trans in state.get('transitions', []):
                    if trans.get('actions'):
                        normalize_actions(trans['actions'])
                if state.get('states'):
                    traverse_and_normalize(state)

    if business_flow:
        if business_flow.get('states'):
            traverse_and_normalize({'states': business_flow['states']})
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                traverse_and_normalize(region)

    # ---------- Defer / Timeline 动作处理 ----------
    defer_actions = []
    defer_counter = 0
    defer_timer_names = []

    def process_defer(action_list, defer_counter):
        new_actions = []
        for act in action_list:
            if act.startswith('timeline:'):
                content = act[len('timeline:'):].strip()
                items = [x.strip() for x in content.split(',')]
                for item in items:
                    parts = item.split('=>')
                    if len(parts) == 2:
                        time_ms = parts[0].strip()
                        sub_action = parts[1].strip()
                        timer_name = f"defer_{defer_counter}"
                        new_actions.append(f"start_timer {timer_name} {time_ms}")
                        defer_actions.append({
                            'timer_name': timer_name,
                            'sub_action': sub_action
                        })
                        defer_timer_names.append(timer_name)
                        defer_counter += 1
            elif act.startswith('defer '):
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
                        defer_timer_names.append(timer_name)
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

    # ---------- 收集所有定时器事件名 ----------
    timer_events = set()

    def collect_timer_events_from_states(states, prefix=''):
        for state in states:
            for trans in state.get('transitions', []):
                for action in trans.get('actions', []):
                    if 'start_timer' in action:
                        timer_name = action.split(' ')[1]
                        timer_events.add(f"EVENT_TIMER_EXPIRED_{timer_name}")
            for action in state.get('on_entry', []):
                if 'start_timer' in action:
                    timer_name = action.split(' ')[1]
                    timer_events.add(f"EVENT_TIMER_EXPIRED_{timer_name}")
            for action in state.get('on_exit', []):
                if 'start_timer' in action:
                    timer_name = action.split(' ')[1]
                    timer_events.add(f"EVENT_TIMER_EXPIRED_{timer_name}")
            if state.get('after'):
                timer_events.add(f"EVENT_TIMER_EXPIRED_{prefix}{state['name']}_timeout")
            if state.get('states'):
                collect_timer_events_from_states(state['states'], prefix)

    if business_flow:
        if business_flow.get('states'):
            collect_timer_events_from_states(business_flow['states'])
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                collect_timer_events_from_states(region['states'], region['name'] + '_')

    # ---------- 收集所有 publish / publish_async 事件 ----------
    published_events = set()

    def extract_publish_events(action_str: str):
        """从动作字符串中提取 publish / publish_async / send_to 的事件名"""
        events = set()
        # 直接发布动作
        if action_str.startswith('publish ') or action_str.startswith('publish_async '):
            events.add(action_str.split()[-1])
        # send_to 跨区域事件：send_to led_region LED_ON
        elif action_str.startswith('send_to '):
            parts = action_str.split(' ')
            if len(parts) >= 3:
                events.add(parts[2])
        # defer 内嵌发布：defer 1000 => publish FOO
        elif action_str.startswith('defer ') and '=>' in action_str:
            sub = action_str.split('=>', 1)[1].strip()
            if sub.startswith('publish ') or sub.startswith('publish_async '):
                events.add(sub.split()[-1])
        # timeline 内嵌发布：timeline: 1000=>publish FOO, 2000=>publish BAR
        elif action_str.startswith('timeline:') and '=>' in action_str:
            # 提取 "timeline: " 之后的部分
            content = action_str.split(':', 1)[1].strip() if ':' in action_str else action_str
            for part in content.split(','):
                if '=>' in part:
                    sub = part.split('=>', 1)[1].strip()
                    if sub.startswith('publish ') or sub.startswith('publish_async '):
                        events.add(sub.split()[-1])
        # when 条件发布：when condition => publish_async EVENT
        elif '=>' in action_str:
            sub = action_str.split('=>', 1)[1].strip()
            if sub.startswith('publish ') or sub.startswith('publish_async '):
                events.add(sub.split()[-1])
        return events

    def collect_published_events(states):
        for state in states:
            for trans in state.get('transitions', []):
                for action in trans.get('actions', []):
                    published_events.update(extract_publish_events(action))
            for action in state.get('on_entry', []):
                published_events.update(extract_publish_events(action))
            for action in state.get('on_exit', []):
                published_events.update(extract_publish_events(action))
            if state.get('states'):
                collect_published_events(state['states'])

    if business_flow:
        if business_flow.get('states'):
            collect_published_events(business_flow['states'])
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                collect_published_events(region['states'])

    # 同时从已经处理好的 defer_actions 中提取 publish 事件
    # （traverse_states 已将 "defer 1000 => publish FOO" 替换为 "start_timer defer_N 1000"，
    #   原始 publish 动作被移入 defer_actions[].sub_action）
    for d in defer_actions:
        sub = d.get('sub_action', '')
        if sub.startswith('publish ') or sub.startswith('publish_async '):
            published_events.add(sub.split()[-1])

    # ---------- 收集所有 transition event 名称（非内置事件、非定时器事件）----------
    BUILTIN_EVENTS = {
        'BUTTON_PRESS', 'RTC_TICK', 'RTC_ALARM', 'RETURN',
        'MINUTE_TICK', 'HOUR_TICK', 'MPU6050_ALERT',
    }
    transition_events = set()

    def collect_transition_events(states):
        for state in states:
            for trans in state.get('transitions', []):
                evt_name = trans.get('event', '')
                evt_upper = evt_name.replace(' ', '_').upper()
                if evt_name and evt_upper not in BUILTIN_EVENTS:
                    event_key = evt_name.replace(' ', '_')
                    # Skip timer expiry events (handled by timer_events separately)
                    if event_key.startswith('TIMER_EXPIRED_'):
                        continue
                    # Skip events already collected as published_events
                    if event_key not in published_events:
                        transition_events.add(event_key)
            if state.get('states'):
                collect_transition_events(state['states'])

    if business_flow:
        if business_flow.get('states'):
            collect_transition_events(business_flow['states'])
        if business_flow.get('regions'):
            for region in business_flow['regions']:
                collect_transition_events(region['states'])

    # ---------- Auto-inject RTC driver when business flow needs timers ----------
    # Demos with timer_events or defer_actions need the software timer
    # infrastructure from drv_rtc, even if no explicit Internal_RTC peripheral
    # is declared.  Inject a synthetic driver entry so drv_rtc.c/h are generated.
    if (timer_events or defer_actions) and not has_rtc:
        has_rtc = True
        rtc_model = load_model('Internal_RTC')
        synth_peripheral = {
            'name': 'rtc',
            'type': 'Internal_RTC',
            'interface': 'internal',
            'model': rtc_model,
        }
        drivers.append({
            'name': 'rtc',
            'template': rtc_model.get('driver_template', ''),
            'header_template': rtc_model.get('header_template', ''),
            'model': rtc_model,
            'peripheral': synth_peripheral,
        })
        peripherals.append(synth_peripheral)
        # HAL sources for RTC and TIM (needed for drv_rtc.c)
        for rtc_hal in ['stm32g0xx_hal_rtc.c', 'stm32g0xx_hal_rtc_ex.c',
                         'stm32g0xx_hal_tim.c', 'stm32g0xx_hal_tim_ex.c']:
            if rtc_hal not in hal_sources:
                hal_sources.append(rtc_hal)

    # ---------- 静态库绝对路径 ----------
    static_dir_absolute = os.path.abspath(STATIC_STM32_DIR).replace("\\", "/")

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
        "rtc_async_prediv": 127 if has_rtc else None,
        "rtc_sync_prediv": 255 if has_rtc else None,
        "has_pwm": has_pwm,
        "has_spi": has_spi,
        "has_spi_flash": has_spi_flash,
        "has_mpu6050": has_mpu6050,
        "has_adc": has_adc,
        "has_uart": has_uart,
        "has_rs485": has_rs485,
        "has_ir": has_ir,
        "has_cellular": has_cellular,
        "has_modbus": has_modbus,
        "has_mqtt": has_mqtt,
        "has_cli": has_cli,
        "uart_name": uart_name,
        "rs485_name": rs485_name,
        "modbus_name": modbus_name,
        "cli_uart_name": cli_uart_name,
        "has_led": has_led,
        "has_led_task": has_led_task,
        "has_log": has_log,
        "has_tickless": has_tickless,
        "has_business_flow": has_business_flow,
        "business_flow": business_flow,
        "has_substate": has_substate,
        "has_bootloader": has_bootloader,
        "has_fota": has_fota,
        "boot_config": boot_config,
        "boot_max_retries": boot_config.get('max_retries', 3),
        "iwdg_reload_value": boot_config.get('iwdg_reload_value', 625) if has_bootloader else None,
        "hil": hil_config,
        "hil_tests": hil_tests,
        "hil_mode": hil_mode,
        "heap_size": hw.get("heap_size", "0x200"),
        "stack_size": hw.get("stack_size", "0x400"),
        "static_dir_absolute": static_dir_absolute,
        "has_event_mgr": True,
        "defer_actions": defer_actions,
        "defer_timer_names": defer_timer_names,
        "timer_events": sorted(timer_events),
        "published_events": sorted(published_events),
        "transition_events": sorted(transition_events),
    }

    return context
