"""
pin_context.py
Pin processing logic: adds default values for exti, notify_task, af fields.
"""


def process_pins(pins: list) -> list:
    """
    Add default values to each pin dict for missing fields.

    Args:
        pins: list of pin dicts from hardware YAML.

    Returns:
        The same list with defaults applied in-place.
    """
    for pin in pins:
        if pin.get("exti") is None:
            pin["exti"] = {}
        if "notify_task" not in pin:
            pin["notify_task"] = ""
        if "af" not in pin:
            pin["af"] = 0
    return pins
