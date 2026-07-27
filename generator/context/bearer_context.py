"""
bearer_context.py
Associates protocol-layer peripherals (Modbus, MQTT) with their physical-layer bearer.
"""


def associate_bearers(peripherals: list, drivers: list) -> dict:
    """
    Link protocol peripherals to communication bearers.
    Returns dict with: has_mqtt, has_modbus, modbus_name
    """
    has_modbus = False
    has_mqtt = False
    modbus_name = ""

    for p in peripherals:
        if p.get('type') == 'Protocol_MQTT':
            has_mqtt = True
        if p.get('type') == 'Protocol_Modbus':
            has_modbus = True
            modbus_name = p.get('name', '')

    return {
        'has_mqtt': has_mqtt,
        'has_modbus': has_modbus,
        'modbus_name': modbus_name,
    }
