import re
import os


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
            if pin.get('function') and pin['function'] not in valid_functions:
                errors.append(f"[ERROR] Pin #{i} ('{pin.get('id', 'unknown')}') has invalid function '{pin['function']}'. Valid options: {valid_functions}")

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
        
        if not ('states' in bf or 'regions' in bf):
            errors.append("[ERROR] business_flow has neither 'states' nor 'regions' defined.")

        valid_actions = ['toggle_led', 'return', 'EVENT_NONE']
        valid_action_prefixes = ['start_timer ', 'stop_timer ', 'set ', 'calc ', 'publish ', 'publish_async ', 'when ', 'defer ', 'timeline:', 'send_to ']
        state_names = []

        def validate_actions(action_list, location):
            for action in action_list:
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
                if state.get('on_exit'):
                    validate_actions(state['on_exit'], f"on_exit of state '{state.get('name', 'unknown')}'")

                for j, trans in enumerate(state.get('transitions', [])):
                    if 'event' not in trans:
                        errors.append(f"[ERROR] Transition #{j} in state '{state.get('name', 'unknown')}' has no 'event' field.")
                    if 'target' not in trans:
                        errors.append(f"[ERROR] Transition #{j} in state '{state.get('name', 'unknown')}' has no 'target' field.")
                    if trans.get('actions'):
                        validate_actions(trans['actions'], f"transition #{j} of state '{state.get('name', 'unknown')}'")
                    if trans.get('guard'):
                        errors.append(f"[INFO] Guard condition '{trans['guard']}' in transition #{j} of state '{state.get('name', 'unknown')}' will be used as-is without validation.")

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
                        if substate.get('on_exit'):
                            validate_actions(substate['on_exit'], f"on_exit of substate '{substate_full_name}'")
                        for l, subtrans in enumerate(substate.get('transitions', [])):
                            if 'event' not in subtrans:
                                errors.append(f"[ERROR] Transition #{l} in substate '{substate_full_name}' has no 'event' field.")
                            if subtrans.get('actions'):
                                validate_actions(subtrans['actions'], f"transition #{l} of substate '{substate_full_name}'")

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
                        if state.get('on_exit'):
                            validate_actions(state['on_exit'], f"on_exit of state '{state_full_name}'")
                        for k, trans in enumerate(state.get('transitions', [])):
                            if 'event' not in trans:
                                errors.append(f"[ERROR] Transition #{k} in state '{state_full_name}' has no 'event' field.")
                            if 'target' not in trans:
                                errors.append(f"[ERROR] Transition #{k} in state '{state_full_name}' has no 'target' field.")
                            if trans.get('actions'):
                                validate_actions(trans['actions'], f"transition #{k} of state '{state_full_name}'")

        if 'variables' in bf:
            for i, var in enumerate(bf['variables']):
                if 'name' not in var or not var['name']:
                    errors.append(f"[ERROR] Variable #{i} in business_flow has no 'name' field.")
                if 'type' not in var or not var['type']:
                    errors.append(f"[ERROR] Variable '{var.get('name', 'unknown')}' has no 'type' field.")
                else:
                    valid_types = ['uint8_t', 'uint16_t', 'uint32_t', 'int8_t', 'int16_t', 'int32_t', 'float', 'bool']
                    if var['type'] not in valid_types:
                        errors.append(f"[WARNING] Variable '{var.get('name', 'unknown')}' has type '{var['type']}' which is not in the recommended list: {valid_types}")

    return errors