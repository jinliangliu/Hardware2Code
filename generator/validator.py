def validate_hardware(hw):
    errors = []
    # 检查必填字段
    if 'mcu' not in hw or 'part' not in hw['mcu']:
        errors.append("Missing 'mcu.part' field in hardware YAML.")
    if 'pins' not in hw or not hw['pins']:
        errors.append("No pins defined in hardware YAML.")

    # 检查引脚重复
    if 'pins' in hw:
        pin_ids = [pin['id'] for pin in hw['pins']]
        duplicates = set([pid for pid in pin_ids if pin_ids.count(pid) > 1])
        if duplicates:
            errors.append(f"Duplicate pin IDs found: {duplicates}")

        # 检查是否有至少一个输出引脚标记为 LED
        if not any(pin.get('label') == 'LED' for pin in hw['pins']):
            errors.append("No pin labeled 'LED' found. LED task needs an output pin.")

    return errors