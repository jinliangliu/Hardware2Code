import re
import os

# ---------- Expression validation helpers ----------

_VALID_C_TYPES = {'uint8_t', 'uint16_t', 'uint32_t', 'int8_t', 'int16_t', 'int32_t', 'float', 'bool'}
_COMPARISON_OPS = {'>', '>=', '<', '<=', '==', '!='}
_C_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _collect_all_variables(hw):
    """
    Collect all declared variable names from business_flow and regions.
    Returns dict: {var_name: var_type_str}
    """
    variables = {}
    bf = hw.get('business_flow', {})
    if not bf:
        return variables

    for var in bf.get('variables', []):
        variables[var['name']] = var.get('type', 'uint32_t')

    for region in bf.get('regions', []):
        prefix = region.get('name', '') + '_'
        for var in region.get('variables', []):
            variables[prefix + var['name']] = var.get('type', 'uint32_t')

    return variables


def _validate_guard(guard_str, variables, location):
    """
    Validate a guard condition string.
    Expected format: "var_name OP literal"
    Returns list of error strings.
    """
    errors = []
    if not guard_str or not guard_str.strip():
        return errors

    expr = guard_str.strip()

    # Try to match: IDENTIFIER OP (literal|IDENTIFIER)
    for op in sorted(_COMPARISON_OPS, key=len, reverse=True):
        if op in expr:
            parts = expr.split(op, 1)
            left = parts[0].strip()
            right = parts[1].strip()
            break
    else:
        # No operator found — might be a boolean variable reference like "flag_name"
        if _C_IDENTIFIER.match(expr):
            if expr not in variables:
                errors.append(f"[ERROR] Guard variable '{expr}' in {location} is not declared in variables list. Available: {sorted(variables.keys())}")
            return errors
        else:
            # Could be a complex C expression — warn but don't error
            errors.append(f"[WARNING] Guard expression '{guard_str}' in {location} could not be parsed as a simple comparison. It will be used as-is.")
            return errors

    # Check left side (must be a declared variable)
    if not _C_IDENTIFIER.match(left):
        errors.append(f"[WARNING] Guard left-hand side '{left}' in {location} does not look like a variable name. It will be used as-is.")
    elif left not in variables:
        errors.append(f"[ERROR] Guard variable '{left}' in {location} is not declared in variables list. Available: {sorted(variables.keys())}")

    # Check right side (can be a literal number, another variable, or a constant)
    if right.isdigit() or (right.startswith('0x') and all(c in '0123456789abcdefABCDEF' for c in right[2:])):
        pass  # Numeric literal — OK
    elif _C_IDENTIFIER.match(right):
        if right not in variables:
            errors.append(f"[INFO] Guard right-hand side '{right}' in {location} is not a declared variable. Assuming it is a C constant or macro.")
    else:
        errors.append(f"[INFO] Guard right-hand side '{right}' in {location} is a complex expression. It will be used as-is.")

    return errors


def _validate_calc(calc_str, variables, location):
    """
    Validate a calc expression string.
    Expected format: "dest_var = expression"
    Returns list of error strings.
    """
    errors = []
    if not calc_str or not calc_str.strip():
        return errors

    expr = calc_str.strip()
    if '=' not in expr:
        errors.append(f"[ERROR] Calc expression '{calc_str}' in {location} missing '='. Format: 'dest = expression'.")
        return errors

    parts = expr.split('=', 1)
    dest = parts[0].strip()
    rhs = parts[1].strip()

    if not _C_IDENTIFIER.match(dest):
        errors.append(f"[ERROR] Calc destination '{dest}' in {location} is not a valid variable name.")
    elif dest not in variables:
        errors.append(f"[ERROR] Calc destination variable '{dest}' in {location} is not declared. Available: {sorted(variables.keys())}")

    # Extract identifiers from RHS and check them
    rhs_tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', rhs)
    for token in rhs_tokens:
        if token not in variables and token not in {'inc', 'dec'}:
            errors.append(f"[INFO] Calc references '{token}' in {location} which is not a declared variable. Assuming C constant/macro.")

    return errors


def _validate_when(when_str, variables, location):
    """
    Validate a when condition+action string.
    Expected format: "var OP literal => action"
    Returns list of error strings.
    """
    errors = []
    if not when_str or not when_str.strip():
        return errors

    expr = when_str.strip()

    if '=>' not in expr:
        errors.append(f"[ERROR] When expression '{when_str}' in {location} missing '=>' separator. Format: 'condition => action'.")
        return errors

    cond_part, action_part = expr.split('=>', 1)
    cond = cond_part.strip()
    action = action_part.strip()

    # Validate the condition part using the same logic as guards
    for op in sorted(_COMPARISON_OPS, key=len, reverse=True):
        if op in cond:
            parts = cond.split(op, 1)
            left = parts[0].strip()
            right = parts[1].strip()
            break
    else:
        # No operator — treat as boolean variable
        if _C_IDENTIFIER.match(cond) and cond not in variables:
            errors.append(f"[ERROR] When condition variable '{cond}' in {location} is not declared. Available: {sorted(variables.keys())}")
        if not _C_IDENTIFIER.match(cond):
            errors.append(f"[WARNING] When condition '{cond}' in {location} is complex. It will be used as-is.")
        return errors

    if not _C_IDENTIFIER.match(left):
        errors.append(f"[WARNING] When left-hand side '{left}' in {location} does not look like a variable name.")
    elif left not in variables:
        errors.append(f"[ERROR] When variable '{left}' in {location} is not declared. Available: {sorted(variables.keys())}")

    # Validate the action part (basic check — it should be a known action)
    return errors


# ---------- Main validator ----------


def _validate_extra_fields(peripheral, model_path, errors):
    """
    Validate peripheral extra fields against model's extra_schema.
    """
    import yaml
    try:
        with open(model_path, 'r', encoding='utf-8') as f:
            model = yaml.safe_load(f)
    except Exception:
        return

    schema = model.get('extra_schema', {})
    if not schema:
        return

    extra = peripheral.get('extra', {})
    pname = peripheral.get('name', 'unknown')

    for field_name, field_schema in schema.items():
        field_type = field_schema.get('type', 'str')
        required = field_schema.get('required', False)
        default = field_schema.get('default')
        allowed_values = field_schema.get('values')

        if field_name not in extra:
            if required:
                errors.append(f"[ERROR] Peripheral '{pname}' is missing required extra field '{field_name}'.")
            continue

        value = extra[field_name]

        # Type check
        if field_type == 'int' and not isinstance(value, int):
            errors.append(f"[ERROR] Peripheral '{pname}' extra field '{field_name}' must be an integer, got '{value}'.")
        elif field_type == 'str' and not isinstance(value, str):
            errors.append(f"[ERROR] Peripheral '{pname}' extra field '{field_name}' must be a string, got '{value}'.")
        elif field_type == 'pin':
            if not isinstance(value, str) or not re.match(r'^P[A-F][0-9]{1,2}$', value):
                errors.append(f"[ERROR] Peripheral '{pname}' extra field '{field_name}' must be a valid pin ID (e.g. PA2), got '{value}'.")

        # Enum check
        if allowed_values and value not in allowed_values:
            errors.append(f"[WARNING] Peripheral '{pname}' extra field '{field_name}' value '{value}' is not in recommended list: {allowed_values}.")


def validate_hardware(hw):
    errors = []

    if 'mcu' not in hw or 'part' not in hw['mcu']:
        errors.append("[CRITICAL] Missing 'mcu.part' field in hardware YAML.")
    else:
        mcu_part = hw['mcu']['part']
        if not re.match(r'^STM32[A-Z0-9]+$', mcu_part):
            errors.append(f"[ERROR] Invalid MCU part number format: '{mcu_part}'. Expected format like 'STM32G0B1RET6'.")

    if 'pins' not in hw or not hw['pins']:
        errors.append("[WARNING] No pins defined in hardware YAML.")
    else:
        pin_ids = []
        for i, pin in enumerate(hw['pins']):
            if 'id' not in pin or not pin['id']:
                errors.append(f"[ERROR] Pin #{i} has no 'id' field.")
            else:
                pin_id = pin['id']
                if not re.match(r'^P[A-F][0-9]$|^P[A-F][0-9][0-9]$', pin_id):
                    errors.append(f"[ERROR] Invalid pin ID format '{pin_id}' at pin #{i}. Expected format like 'PA0' or 'PC13'.")
                pin_ids.append(pin_id)

            if 'function' not in pin or not pin['function']:
                errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has no 'function' field.")

            valid_functions = ['GPIO_Output', 'GPIO_Input', 'I2C_SCL', 'I2C_SDA', 'SPI_SCK', 'SPI_MISO', 'SPI_MOSI', 'SPI_NSS', 'UART_TX', 'UART_RX', 'USART_TX', 'USART_RX', 'LPUART_TX', 'LPUART_RX', 'ADC_IN']
            valid_function_patterns = [
                r'^I2C\d+_SCL$', r'^I2C\d+_SDA$',
                r'^SPI\d+_SCK$', r'^SPI\d+_MISO$', r'^SPI\d+_MOSI$', r'^SPI\d+_NSS$',
                r'^USART\d+_TX$', r'^USART\d+_RX$', r'^UART\d+_TX$', r'^UART\d+_RX$',
                r'^ADC_IN\d+$',
            ]
            if pin.get('function') and pin['function'] not in valid_functions:
                # Check against regex patterns for numbered variants
                if not any(re.match(p, pin['function']) for p in valid_function_patterns):
                    errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has invalid function '{pin['function']}'. Valid options: {valid_functions} or numbered variants like I2C1_SCL, SPI1_SCK, USART2_TX, ADC_IN1.")

            if pin.get('pull') and pin['pull'] not in ['up', 'down', None]:
                errors.append(f"[WARNING] Pin #{i} ('{pin.get('id', 'unknown')}') has invalid pull value '{pin['pull']}'. Valid options: 'up', 'down'.")

            if pin.get('exti') and pin['exti'].get('enable'):
                if not pin.get('exti', {}).get('trigger'):
                    errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has EXTI enabled but no trigger specified.")
                elif pin['exti']['trigger'] not in ['rising', 'falling', 'both']:
                    errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has invalid EXTI trigger '{pin['exti']['trigger']}'. Valid options: 'rising', 'falling', 'both'.")

        duplicates = set([pid for pid in pin_ids if pin_ids.count(pid) > 1])
        if duplicates:
            errors.append(f"[ERROR] Duplicate pin IDs found: {duplicates}")

        has_led = any(pin.get('label') == 'LED' for pin in hw['pins'])
        has_led_task = any(t.get('name') == 'led_task' for t in hw.get('app_tasks', []))
        if has_led_task and not has_led:
            errors.append("[ERROR] 'led_task' defined but no pin labeled 'LED' found. LED task needs an output pin.")

    if 'app_tasks' in hw:
        for i, task in enumerate(hw['app_tasks']):
            if 'name' not in task or not task['name']:
                errors.append(f"[ERROR] Task #{i} has no 'name' field.")

            if 'priority' in task:
                if not isinstance(task['priority'], int) or task['priority'] < 0 or task['priority'] > 31:
                    errors.append(f"[ERROR] Task '{task.get('name', 'unknown')}' has invalid priority '{task['priority']}'. Must be integer 0-31.")

            if 'stack_size' in task:
                if not isinstance(task['stack_size'], int) or task['stack_size'] <= 0:
                    errors.append(f"[ERROR] Task '{task.get('name', 'unknown')}' has invalid stack_size '{task['stack_size']}'. Must be positive integer.")

    if 'peripherals' in hw:
        for i, p in enumerate(hw['peripherals']):
            if 'name' not in p or not p['name']:
                errors.append(f"[ERROR] Peripheral #{i} has no 'name' field.")

            if 'type' not in p or not p['type']:
                errors.append(f"[ERROR] Peripheral #{i} ('{p.get('name', 'unknown')}') has no 'type' field.")

            valid_types = ['Internal_RTC', 'Internal_PWM', 'Internal_ADC', 'UART_Serial', 'I2C_Sensor_MPU6050', 'SPI_Flash_W25Q32']
            if p.get('type') and p['type'] not in valid_types:
                errors.append(f"[ERROR] Peripheral #{i} ('{p.get('name', 'unknown')}') has invalid type '{p['type']}'. Valid options: {valid_types}")

            if p.get('type') in ['I2C_Sensor_MPU6050'] and 'bus' not in p:
                errors.append(f"[ERROR] I2C peripheral '{p.get('name', 'unknown')}' is missing 'bus' field (e.g., 'I2C1').")

            if p.get('type') in ['SPI_Flash_W25Q32'] and 'bus' not in p:
                errors.append(f"[ERROR] SPI peripheral '{p.get('name', 'unknown')}' is missing 'bus' field (e.g., 'SPI1').")

            model_path = os.path.join('models', p['type'] + '.yaml')
            if not os.path.exists(model_path):
                errors.append(f"[WARNING] Model file '{model_path}' for peripheral type '{p['type']}' not found. Some features may not work.")
            else:
                # Validate extra fields against model's extra_schema
                _validate_extra_fields(p, model_path, errors)

    if 'sleep' in hw and hw['sleep'].get('mode'):
        valid_modes = ['STOP0', 'STOP1', 'STOP2', 'STANDBY', 'SLEEP']
        if hw['sleep']['mode'] not in valid_modes:
            errors.append(f"[WARNING] Invalid sleep mode '{hw['sleep']['mode']}'. Valid options: {valid_modes}")

    if 'bootloader' in hw and hw['bootloader']:
        bl = hw['bootloader']
        if bl.get('enabled'):
            size_kb = bl.get('size_kb', 8)
            if not isinstance(size_kb, int) or size_kb < 4 or size_kb > 32:
                errors.append(f"[ERROR] Bootloader size_kb '{size_kb}' is invalid. Must be 4-32 (KB).")

            max_retries = bl.get('max_retries', 3)
            if not isinstance(max_retries, int) or max_retries < 1 or max_retries > 10:
                errors.append(f"[ERROR] Bootloader max_retries '{max_retries}' is invalid. Must be 1-10.")

            app_a = bl.get('app_a_offset', 0x2000)
            app_b = bl.get('app_b_offset', 0x40000)
            if app_a >= app_b:
                errors.append(f"[ERROR] Bootloader app_a_offset (0x{app_a:X}) must be less than app_b_offset (0x{app_b:X}).")

            if app_a < size_kb * 1024:
                errors.append(f"[ERROR] Bootloader app_a_offset (0x{app_a:X}) must be >= bootloader size ({size_kb}KB = 0x{size_kb*1024:X}).")

    if 'business_flow' in hw and hw['business_flow']:
        bf = hw['business_flow']

        # Collect all declared variables for expression validation
        _all_vars = _collect_all_variables(hw)

        # ---------- Optional events declaration ----------
        if 'events' in bf:
            valid_event_sources = {'exti', 'rtc', 'timer', 'custom'}
            valid_event_types = {'synchronous', 'asynchronous'}
            for i, evt in enumerate(bf['events']):
                if 'name' not in evt or not evt['name']:
                    errors.append(f"[ERROR] Event #{i} in business_flow.events has no 'name' field.")
                if evt.get('source') and evt['source'] not in valid_event_sources:
                    errors.append(f"[WARNING] Event '{evt.get('name', 'unknown')}' has unknown source '{evt['source']}'. Valid: {sorted(valid_event_sources)}.")
                if evt.get('type') and evt['type'] not in valid_event_types:
                    errors.append(f"[WARNING] Event '{evt.get('name', 'unknown')}' has unknown type '{evt['type']}'. Valid: {sorted(valid_event_types)}.")

        if not ('states' in bf or 'regions' in bf):
            errors.append("[ERROR] business_flow has neither 'states' nor 'regions' defined.")

        valid_actions = ['toggle_led', 'return', 'EVENT_NONE']
        valid_action_prefixes = ['start_timer ', 'stop_timer ', 'set ', 'calc ', 'publish ', 'publish_async ', 'when ', 'defer ', 'timeline:', 'send_to ']
        state_names = []

        def validate_actions(action_list, location):
            for idx, action in enumerate(action_list):
                # Support new dict-format actions: {toggle_led: null}, {defer: {after: 3000, do: ...}}, etc.
                if isinstance(action, dict):
                    action_keys = list(action.keys())
                    if len(action_keys) != 1:
                        errors.append(f"[ERROR] Dict-format action #{idx} in {location} must have exactly one key. Got: {action_keys}")
                        continue
                    action_name = action_keys[0]
                    if action_name in valid_actions:
                        continue  # Simple actions like toggle_led
                    elif action_name == 'timeline':
                        # timeline: [{ms: N, do: ACTION}, ...]
                        continue
                    elif action_name in ('defer', 'start_timer', 'stop_timer', 'set', 'calc',
                                         'publish', 'publish_async', 'when', 'send_to'):
                        continue
                    else:
                        errors.append(f"[ERROR] Unknown dict-format action '{action_name}' in {location}.")
                    continue

                # String-format action (legacy)
                if not isinstance(action, str):
                    errors.append(f"[ERROR] Action #{idx} in {location} must be a string or dict, got {type(action).__name__}.")
                    continue

                is_valid = False
                if action in valid_actions:
                    is_valid = True
                else:
                    for prefix in valid_action_prefixes:
                        if action.startswith(prefix):
                            is_valid = True
                            break
                if not is_valid:
                    errors.append(f"[ERROR] Unknown action '{action}' in {location}.")

        def validate_expressions_in_actions(action_list, location):
            """Validate guard/calc/when expressions within action strings or dicts."""
            for action in action_list:
                # Dict-format action: extract the action type and params
                if isinstance(action, dict):
                    action_key = list(action.keys())[0]
                    params = action[action_key] or {}
                    if action_key == 'when':
                        cond = params.get('cond', '')
                        if cond:
                            errors.extend(_validate_when(f"{cond} => _", _all_vars, location))
                    elif action_key == 'calc':
                        params_dict = params if isinstance(params, dict) else {}
                        expr = params_dict.get('expr', '')
                        dest = params_dict.get('var', '')
                        if expr and dest:
                            errors.extend(_validate_calc(f"{dest} = {expr}", _all_vars, location))
                    continue

                # String-format action
                if not isinstance(action, str):
                    continue
                if action.startswith('calc '):
                    calc_expr = action[5:].strip()
                    errors.extend(_validate_calc(calc_expr, _all_vars, location))
                elif action.startswith('when '):
                    when_expr = action[5:].strip()
                    errors.extend(_validate_when(when_expr, _all_vars, location))
                elif action.startswith('defer '):
                    # Check if defer's sub-action is a when/calc
                    if '=>' in action:
                        sub = action.split('=>', 1)[1].strip()
                        if sub.startswith('when '):
                            errors.extend(_validate_when(sub[5:].strip(), _all_vars, f"{location} (defer sub-action)"))
                        elif sub.startswith('calc '):
                            errors.extend(_validate_calc(sub[5:].strip(), _all_vars, f"{location} (defer sub-action)"))
                elif action.startswith('timeline:'):
                    content = action.split(':', 1)[1].strip() if ':' in action else action
                    for part in content.split(','):
                        if '=>' in part:
                            sub = part.split('=>', 1)[1].strip()
                            if sub.startswith('when '):
                                errors.extend(_validate_when(sub[5:].strip(), _all_vars, f"{location} (timeline sub-action)"))
                            elif sub.startswith('calc '):
                                errors.extend(_validate_calc(sub[5:].strip(), _all_vars, f"{location} (timeline sub-action)"))

        if 'states' in bf and bf['states']:
            for i, state in enumerate(bf['states']):
                if 'name' not in state or not state['name']:
                    errors.append(f"[ERROR] State #{i} in business_flow has no 'name' field.")
                else:
                    state_names.append(state['name'])

                if state.get('states') and not state.get('initial_state'):
                    errors.append(f"[ERROR] Compound state '{state.get('name', 'unknown')}' has sub-states but no initial_state.")

                if state.get('on_entry'):
                    validate_actions(state['on_entry'], f"on_entry of state '{state.get('name', 'unknown')}'")
                    validate_expressions_in_actions(state['on_entry'], f"on_entry of state '{state.get('name', 'unknown')}'")
                if state.get('on_exit'):
                    validate_actions(state['on_exit'], f"on_exit of state '{state.get('name', 'unknown')}'")
                    validate_expressions_in_actions(state['on_exit'], f"on_exit of state '{state.get('name', 'unknown')}'")

                for j, trans in enumerate(state.get('transitions', [])):
                    if 'event' not in trans:
                        errors.append(f"[ERROR] Transition #{j} in state '{state.get('name', 'unknown')}' has no 'event' field.")
                    if 'target' not in trans:
                        errors.append(f"[ERROR] Transition #{j} in state '{state.get('name', 'unknown')}' has no 'target' field.")
                    if trans.get('actions'):
                        validate_actions(trans['actions'], f"transition #{j} of state '{state.get('name', 'unknown')}'")
                        validate_expressions_in_actions(trans['actions'], f"transition #{j} of state '{state.get('name', 'unknown')}'")
                    if trans.get('guard'):
                        errors.extend(_validate_guard(trans['guard'], _all_vars, f"guard of transition #{j} in state '{state.get('name', 'unknown')}'"))

                if state.get('type') == 'ref':
                    ref_file = state.get('ref')
                    if not ref_file:
                        errors.append(f"[ERROR] State '{state.get('name', 'unknown')}' is a 'ref' type but has no 'ref' field.")
                    else:
                        ref_path = os.path.join('examples', ref_file)
                        if not os.path.exists(ref_path) and not os.path.exists(ref_file):
                            errors.append(f"[ERROR] Ref file '{ref_file}' not found for state '{state.get('name', 'unknown')}'. Searched in: '{ref_path}' and '{ref_file}'.")
                    if not state.get('namespace'):
                        errors.append(f"[WARNING] State '{state.get('name', 'unknown')}' is a 'ref' type but has no 'namespace'. Variable/state name conflicts may occur.")

                if state.get('states'):
                    for k, substate in enumerate(state['states']):
                        substate_full_name = f"{state['name']}.{substate.get('name', 'unknown')}"
                        state_names.append(substate_full_name)
                        if 'name' not in substate or not substate['name']:
                            errors.append(f"[ERROR] Substate #{k} in state '{state.get('name', 'unknown')}' has no 'name' field.")
                        if substate.get('on_entry'):
                            validate_actions(substate['on_entry'], f"on_entry of substate '{substate_full_name}'")
                            validate_expressions_in_actions(substate['on_entry'], f"on_entry of substate '{substate_full_name}'")
                        if substate.get('on_exit'):
                            validate_actions(substate['on_exit'], f"on_exit of substate '{substate_full_name}'")
                            validate_expressions_in_actions(substate['on_exit'], f"on_exit of substate '{substate_full_name}'")
                        for l, subtrans in enumerate(substate.get('transitions', [])):
                            if 'event' not in subtrans:
                                errors.append(f"[ERROR] Transition #{l} in substate '{substate_full_name}' has no 'event' field.")
                            if subtrans.get('actions'):
                                validate_actions(subtrans['actions'], f"transition #{l} of substate '{substate_full_name}'")
                                validate_expressions_in_actions(subtrans['actions'], f"transition #{l} of substate '{substate_full_name}'")

        if 'regions' in bf and bf['regions']:
            for i, region in enumerate(bf['regions']):
                if 'name' not in region or not region['name']:
                    errors.append(f"[ERROR] Region #{i} has no 'name' field.")
                if 'initial_state' not in region:
                    errors.append(f"[ERROR] Region '{region.get('name', 'unknown')}' has no 'initial_state' field.")
                if region.get('states'):
                    for j, state in enumerate(region['states']):
                        state_full_name = f"{region['name']}.{state.get('name', 'unknown')}"
                        state_names.append(state_full_name)
                        if 'name' not in state or not state['name']:
                            errors.append(f"[ERROR] State #{j} in region '{region.get('name', 'unknown')}' has no 'name' field.")
                        if state.get('on_entry'):
                            validate_actions(state['on_entry'], f"on_entry of state '{state_full_name}'")
                            validate_expressions_in_actions(state['on_entry'], f"on_entry of state '{state_full_name}'")
                        if state.get('on_exit'):
                            validate_actions(state['on_exit'], f"on_exit of state '{state_full_name}'")
                            validate_expressions_in_actions(state['on_exit'], f"on_exit of state '{state_full_name}'")
                        for k, trans in enumerate(state.get('transitions', [])):
                            if 'event' not in trans:
                                errors.append(f"[ERROR] Transition #{k} in state '{state_full_name}' has no 'event' field.")
                            if 'target' not in trans:
                                errors.append(f"[ERROR] Transition #{k} in state '{state_full_name}' has no 'target' field.")
                            if trans.get('actions'):
                                validate_actions(trans['actions'], f"transition #{k} of state '{state_full_name}'")
                                validate_expressions_in_actions(trans['actions'], f"transition #{k} of state '{state_full_name}'")

        if 'variables' in bf:
            for i, var in enumerate(bf['variables']):
                if 'name' not in var or not var['name']:
                    errors.append(f"[ERROR] Variable #{i} in business_flow has no 'name' field.")
                if 'type' not in var or not var['type']:
                    errors.append(f"[ERROR] Variable '{var.get('name', 'unknown')}' has no 'type' field.")
                else:
                    if var['type'] not in _VALID_C_TYPES:
                        errors.append(f"[WARNING] Variable '{var.get('name', 'unknown')}' has type '{var['type']}' which is not in the recommended list: {sorted(_VALID_C_TYPES)}")

    return errors