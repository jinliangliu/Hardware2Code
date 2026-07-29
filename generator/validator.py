import re
import os
import importlib.util

from .paths import MODELS_DIR, EXAMPLES_DIR

# Load generator/generator_types.py with explicit module name to avoid collision
# with Python's stdlib 'types' module which is frozen at interpreter startup.
_types_spec = importlib.util.spec_from_file_location(
    "hw2c_types",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "generator_types.py")
)
_types_module = importlib.util.module_from_spec(_types_spec)
_types_spec.loader.exec_module(_types_module)
ValidationError = _types_module.ValidationError

# ---------- Expression validation helpers ----------

_VALID_C_TYPES = {'uint8_t', 'uint16_t', 'uint32_t', 'int8_t', 'int16_t', 'int32_t', 'float', 'bool'}
_COMPARISON_OPS = {'>', '>=', '<', '<=', '==', '!='}
_C_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _collect_all_variables(hw: dict) -> dict[str, str]:
    """
    Collect all declared variable names from behavior and regions.
    Returns dict: {var_name: var_type_str}
    """
    variables = {}
    bf = hw.get('behavior', {})
    if not bf:
        return variables

    for var in bf.get('variables', []):
        if 'name' not in var:
            continue
        variables[var['name']] = var.get('type', 'uint32_t')

    for region in bf.get('regions', []):
        prefix = region.get('name', '') + '_'
        for var in region.get('variables', []):
            variables[prefix + var['name']] = var.get('type', 'uint32_t')

    return variables


def _collect_custom_types(hw: dict) -> set[str]:
    """Collect all custom type names from behavior.types."""
    bf = hw.get('behavior', {})
    if not bf:
        return set()
    return {t['name'] for t in bf.get('types', []) if 'name' in t}


def _validate_custom_types(bf: dict) -> list[str]:
    """Validate behavior.types entries."""
    errors = []
    custom_types = set()
    for i, tdef in enumerate(bf.get('types', [])):
        name = tdef.get('name', f'#{i}')
        if not tdef.get('name'):
            errors.append(f"[ERROR] TypeDef #{i} has no 'name' field.")
            continue
        if tdef['name'] in custom_types:
            errors.append(f"[ERROR] Duplicate type name '{tdef['name']}'.")
        custom_types.add(tdef['name'])

        kind = None
        if 'struct' in tdef:
            kind = 'struct'
        elif 'enum' in tdef:
            kind = 'enum'
        elif 'union' in tdef:
            kind = 'union'
        elif 'bitfield' in tdef:
            kind = 'bitfield'

        if kind is None:
            errors.append(f"[ERROR] Type '{name}' must have one of: struct, enum, union, bitfield.")
            continue

        if kind == 'enum':
            values_seen = set()
            for j, ev in enumerate(tdef.get('enum', [])):
                if 'name' not in ev:
                    errors.append(f"[ERROR] Enum value #{j} in '{name}' has no 'name' field.")
                if 'value' in ev and ev['value'] in values_seen:
                    errors.append(f"[ERROR] Duplicate enum value {ev['value']} in '{name}'.")
                if 'value' in ev:
                    values_seen.add(ev['value'])

        if kind == 'bitfield':
            total_width = 0
            for j, bf_member in enumerate(tdef.get('bitfield', [])):
                if 'name' not in bf_member:
                    errors.append(f"[ERROR] Bitfield member #{j} in '{name}' has no 'name' field.")
                if 'width' in bf_member:
                    total_width += bf_member['width']
            if total_width > 64:
                errors.append(f"[WARNING] Bitfield '{name}' total width ({total_width}) exceeds 64 bits.")

        if kind in ('struct', 'union'):
            for j, field in enumerate(tdef.get(kind, [])):
                if 'name' not in field:
                    errors.append(f"[ERROR] {kind.capitalize()} field #{j} in '{name}' has no 'name' field.")
                if 'type' not in field and 'fields' not in field:
                    errors.append(f"[ERROR] {kind.capitalize()} field '{field.get('name', f'#{j}')}' in '{name}' has no 'type' field (required unless it has nested 'fields').")
                if kind == 'struct' and 'fields' in field:
                    for k, nested in enumerate(field.get('fields', [])):
                        if 'name' not in nested:
                            errors.append(f"[ERROR] Nested struct field #{k} in '{name}.{field['name']}' has no 'name' field.")
                        if 'type' not in nested:
                            errors.append(f"[ERROR] Nested struct field '{nested.get('name', f'#{k}')}' in '{name}.{field['name']}' has no 'type' field.")

    return errors


def _validate_guard(guard_str: str, variables: dict[str, str], location: str) -> list[str]:
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


def _validate_calc(calc_str: str, variables: dict[str, str], location: str) -> list[str]:
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


def _validate_when(when_str: str, variables: dict[str, str], location: str) -> list[str]:
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


def _validate_extra_fields(peripheral: dict, model_path: str, errors: list[str]) -> None:
    """
    Validate peripheral extra fields against model's extra_schema.
    """
    import yaml
    try:
        with open(model_path, 'r', encoding='utf-8') as f:
            model = yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
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

        # Check extra dict first, then fall back to top-level peripheral fields
        if field_name in extra:
            value = extra[field_name]
        elif field_name in peripheral:
            value = peripheral[field_name]
        else:
            if required:
                errors.append(f"[ERROR] Peripheral '{pname}' is missing required field '{field_name}'.")
            continue

        # Type check
        if field_type == 'int' and not isinstance(value, int):
            errors.append(f"[ERROR] Peripheral '{pname}' field '{field_name}' must be an integer, got '{value}'.")
        elif field_type == 'str' and not isinstance(value, str):
            errors.append(f"[ERROR] Peripheral '{pname}' field '{field_name}' must be a string, got '{value}'.")
        elif field_type == 'pin':
            if not isinstance(value, str) or not re.match(r'^P[A-F][0-9]{1,2}$', value):
                errors.append(f"[ERROR] Peripheral '{pname}' field '{field_name}' must be a valid pin ID (e.g. PA2), got '{value}'.")

        # Enum check
        if allowed_values and value not in allowed_values:
            errors.append(f"[WARNING] Peripheral '{pname}' field '{field_name}' value '{value}' is not in recommended list: {allowed_values}.")


_ERROR_PREFIX_RE = re.compile(r'\[(CRITICAL|ERROR|WARNING|INFO)\]\s*(.*)')


def _parse_error(raw: str) -> ValidationError:
    """
    Parse a raw error string like '[ERROR] message' into a ValidationError dict.
    Defaults to severity 'ERROR' if prefix is missing.
    """
    m = _ERROR_PREFIX_RE.match(raw)
    if m:
        return ValidationError(severity=m.group(1), message=m.group(2))
    return ValidationError(severity="ERROR", message=raw)


def validate_hardware(hw: dict) -> list[ValidationError]:
    """
    Cross-field business logic validation.

    Type/shape/format validation is handled by Pydantic models (models.py).
    This function only validates cross-referencing and business rules that
    Pydantic cannot express alone.
    """
    errors: list[str] = []

    # MCU and pin shape checks are now handled by Pydantic (McuModel, PinModel).
    # Pin duplicates and LED-task consistency are also handled by HardwareModel.

    if 'pins' not in hw or not hw['pins']:
        errors.append("[WARNING] No pins defined in hardware YAML.")
    else:
        for i, pin in enumerate(hw['pins']):
            if 'function' not in pin or not pin['function']:
                errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has no 'function' field.")

            valid_functions = ['GPIO_Output', 'GPIO_Input', 'I2C_SCL', 'I2C_SDA', 'SPI_SCK', 'SPI_MISO', 'SPI_MOSI', 'SPI_NSS', 'UART_TX', 'UART_RX', 'USART_TX', 'USART_RX', 'LPUART_TX', 'LPUART_RX', 'RS485_DE', 'ADC_IN', 'IR_OUT', 'IR_IN', 'CELL_PWR', 'CELL_RST']
            valid_function_patterns = [
                r'^I2C\d+_SCL$', r'^I2C\d+_SDA$',
                r'^SPI\d+_SCK$', r'^SPI\d+_MISO$', r'^SPI\d+_MOSI$', r'^SPI\d+_NSS$',
                r'^USART\d+_TX$', r'^USART\d+_RX$', r'^UART\d+_TX$', r'^UART\d+_RX$',
                r'^ADC_IN\d+$',
            ]
            if pin.get('function') and pin['function'] not in valid_functions:
                if not any(re.match(p, pin['function']) for p in valid_function_patterns):
                    errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has invalid function '{pin['function']}'. Valid options: {valid_functions} or numbered variants like I2C1_SCL, SPI1_SCK, USART2_TX, ADC_IN1.")

            # EXTI trigger check: Pydantic validates trigger enum values, but
            # the cross-field rule (enabled implies trigger required) remains.
            if pin.get('exti') and pin['exti'].get('enable'):
                if not pin.get('exti', {}).get('trigger'):
                    errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has EXTI enabled but no trigger specified.")

    # Task name/priority/stack_size shape is now handled by Pydantic (TaskModel).

    if 'peripherals' in hw:
        for i, p in enumerate(hw['peripherals']):
            # Peripheral name/type shape is handled by Pydantic (PeripheralModel).
            # Type enum validation is handled by Pydantic.

            if p.get('type') in ['I2C_Sensor_MPU6050', 'I2C_EEPROM'] and 'bus' not in p:
                errors.append(f"[ERROR] I2C peripheral '{p.get('name', 'unknown')}' is missing 'bus' field (e.g., 'I2C1').")

            if p.get('type') in ['SPI_Flash_W25Q32', 'SPI_Flash_Generic'] and 'bus' not in p:
                errors.append(f"[ERROR] SPI peripheral '{p.get('name', 'unknown')}' is missing 'bus' field (e.g., 'SPI1').")

            if p.get('type') in ['Protocol_MQTT']:
                extra = p.get('extra', {})
                bearer_val = p.get('bearer', extra.get('bearer'))
                broker_val = p.get('broker', extra.get('broker'))
                if not bearer_val:
                    errors.append(f"[ERROR] Protocol_MQTT peripheral '{p.get('name', 'unknown')}' is missing required 'bearer' field.")
                else:
                    bearer_found = any(
                        pp.get('name') == bearer_val and pp.get('type') == 'Cellular_4G'
                        for pp in hw.get('peripherals', [])
                    )
                    if not bearer_found:
                        errors.append(f"[ERROR] Protocol_MQTT peripheral '{p.get('name', 'unknown')}' bearer '{bearer_val}' refers to a non-existent Cellular_4G peripheral. Available Cellular_4G: {[pp.get('name') for pp in hw.get('peripherals', []) if pp.get('type') == 'Cellular_4G']}")
                if not broker_val:
                    errors.append(f"[ERROR] Protocol_MQTT peripheral '{p.get('name', 'unknown')}' is missing required 'broker' field.")

            if p.get('type') in ['Protocol_Modbus']:
                extra = p.get('extra', {})
                bearer_val = p.get('bearer', extra.get('bearer'))
                if not bearer_val:
                    errors.append(f"[ERROR] Protocol_Modbus peripheral '{p.get('name', 'unknown')}' is missing required 'bearer' field.")
                else:
                    bearer_found = any(
                        pp.get('name') == bearer_val and pp.get('type') in ['RS485', 'UART_Serial']
                        for pp in hw.get('peripherals', [])
                    )
                    if not bearer_found:
                        errors.append(f"[ERROR] Protocol_Modbus peripheral '{p.get('name', 'unknown')}' bearer '{bearer_val}' refers to a non-existent RS485 or UART peripheral. Available: {[pp.get('name') for pp in hw.get('peripherals', []) if pp.get('type') in ['RS485', 'UART_Serial']]}")

            model_path = os.path.join(MODELS_DIR, p['type'] + '.yaml')
            if not os.path.exists(model_path):
                errors.append(f"[WARNING] Model file '{model_path}' for peripheral type '{p['type']}' not found. Some features may not work.")
            else:
                # Validate extra fields against model's extra_schema
                _validate_extra_fields(p, model_path, errors)

    # Sleep mode enum is handled by Pydantic (SleepModel).
    # Bootloader size_kb, max_retries, and offset constraints are handled
    # by Pydantic (BootloaderModel).

    if 'behavior' in hw and hw['behavior']:
        bf = hw['behavior']

        # Collect all declared variables for expression validation
        _all_vars = _collect_all_variables(hw)

        # ---------- Optional events declaration ----------
        if 'events' in bf:
            valid_event_sources = {'exti', 'rtc', 'timer', 'custom'}
            valid_event_types = {'synchronous', 'asynchronous'}
            for i, evt in enumerate(bf['events']):
                if 'name' not in evt or not evt['name']:
                    errors.append(f"[ERROR] Event #{i} in behavior.events has no 'name' field.")
                if evt.get('source') and evt['source'] not in valid_event_sources:
                    errors.append(f"[WARNING] Event '{evt.get('name', 'unknown')}' has unknown source '{evt['source']}'. Valid: {sorted(valid_event_sources)}.")
                if evt.get('type') and evt['type'] not in valid_event_types:
                    errors.append(f"[WARNING] Event '{evt.get('name', 'unknown')}' has unknown type '{evt['type']}'. Valid: {sorted(valid_event_types)}.")

        if not ('states' in bf or 'regions' in bf):
            errors.append("[ERROR] behavior has neither 'states' nor 'regions' defined.")

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
                    errors.append(f"[ERROR] State #{i} in behavior has no 'name' field.")
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
                        ref_path = os.path.join(EXAMPLES_DIR, ref_file)
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
                        state_full_name = f"{region.get('name', 'unknown')}.{state.get('name', 'unknown')}"
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

        # Validate custom type definitions
        errors += _validate_custom_types(bf)

        if 'variables' in bf:
            custom_type_names = _collect_custom_types(hw)
            for i, var in enumerate(bf['variables']):
                if 'name' not in var or not var['name']:
                    errors.append(f"[ERROR] Variable #{i} in behavior has no 'name' field.")
                if 'type' not in var or not var['type']:
                    errors.append(f"[ERROR] Variable '{var.get('name', 'unknown')}' has no 'type' field.")
                else:
                    if var['type'] not in _VALID_C_TYPES and var['type'] not in custom_type_names:
                        errors.append(f"[WARNING] Variable '{var.get('name', 'unknown')}' has type '{var['type']}' which is not in the recommended list: {sorted(_VALID_C_TYPES)} and not a custom type.")

    return [_parse_error(e) for e in errors]